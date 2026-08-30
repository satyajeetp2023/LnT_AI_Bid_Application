import io
import re
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from decimal import Decimal

from docx import Document as DocxDocument
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, BidDocument, BidRequirement
from app.storage.base import StorageProvider
from app.services.responsibility_assignment import suggest_responsible_function

EXTRACTOR_VERSION = "phase1-requirement-rule-v1"
MIN_CONFIDENCE = .60

@dataclass(frozen=True)
class SourceUnit:
    text: str
    page: int | None = None
    section: str | None = None

@dataclass(frozen=True)
class RequirementCandidate:
    text: str
    page: int | None
    clause: str | None
    section: str | None
    category: str
    requirement_type: str | None
    confidence: float
    priority: str
    is_mandatory: bool

@dataclass(frozen=True)
class ExtractionSummary:
    document_id: int
    created: int
    skipped_duplicates: int
    low_confidence_skipped: int
    no_text: bool
    extractor_version: str = EXTRACTOR_VERSION

CATEGORY_RULES = (
    ("Security / Guarantee Requirement", ("bid security","performance security","bank guarantee","guarantee")),
    ("Financial Requirement", ("turnover","net worth","liquidity","financial capacity")),
    ("Qualification Requirement", ("eligibility","qualification","past experience","similar work","credentials")),
    ("Planning / Scheduling Requirement", ("programme","schedule","milestone","completion period","timeline")),
    ("Testing & Commissioning Requirement", ("testing","commissioning","acceptance test","trial")),
    ("Statutory / Approval Requirement", ("statutory","permit","licence","clearance","authority approval")),
    ("Environmental / Social Requirement", ("environment","environmental","pollution","waste","social")),
    ("Technical Requirement", ("technical specification","performance","technical compliance","equipment specification")),
    ("Commercial Requirement", ("commercial","price","rates","pricing","taxes","payment")),
    ("Contractual Requirement", ("contract","liability","indemnity","termination","obligation")),
    ("Design Requirement", ("design","calculation","drawing","design submission")),
    ("Procurement Requirement", ("vendor","procurement","approved manufacturer")),
    ("Construction Requirement", ("construction","installation","erection","execution")),
    ("Safety Requirement", ("safety","ppe","accident prevention","hse")),
    ("Quality Requirement", ("quality plan","inspection plan","quality assurance","qa","qc")),
    ("Interface Requirement", ("interface","coordination","interfacing agency")),
    ("Insurance Requirement", ("insurance","policy coverage")),
    ("Submission Requirement", ("shall submit","submission","furnish","provide document","to be submitted","submit form")),
    ("Documentation Requirement", ("report","manual","record","document","dossier")),
)
TYPE_RULES = (
    ("Guarantee / Security", ("bank guarantee","bid security","performance security")), ("Eligibility Criterion", ("eligibility","minimum eligibility")),
    ("Experience Requirement", ("similar work","years experience","experience criteria")), ("Financial Criterion", ("turnover","net worth","liquidity")),
    ("Method Statement", ("method statement",)), ("Certificate", ("certificate",)), ("Declaration", ("declaration",)), ("Undertaking", ("undertaking",)),
    ("Evaluation Criterion", ("evaluated based on","evaluation criteria")), ("Technical Compliance", ("comply with technical","meet specification")),
    ("Commercial Compliance", ("commercial compliance","price schedule")), ("Milestone", ("milestone",)), ("Schedule", ("programme","schedule")),
    ("Approval", ("approval","consent")), ("Drawing", ("drawing",)), ("Plan", (" plan ","plan shall")), ("Report", ("report",)),
    ("Form / Format", ("prescribed form","format","annexure","appendix")), ("Document Submission", ("shall submit","furnish","provide document","to be submitted")),
)
STRONG_PHRASES=("shall submit","shall provide","shall furnish","shall ensure","shall comply","shall maintain","shall obtain","shall complete","shall demonstrate","shall include","shall be responsible","is required to","required to","must ","submission shall include","shall be submitted","to be submitted","to be provided","mandatory","minimum requirement")
ACTORS=("bidder shall","contractor shall","tenderer shall","applicant shall","employer requires")
NEGATIVE=("table of contents","copyright","all rights reserved","page intentionally left blank")
CLAUSE_RE=re.compile(r"^(?:(?:clause|section)\s+)?(\d+(?:\.\d+){1,5})\b",re.I)
HEADING_RE=re.compile(r"^(?:section|appendix|schedule|part|chapter)\s+[A-Z0-9]+\b.*",re.I)

class RequirementExtractionProvider(ABC):
    version = EXTRACTOR_VERSION
    @abstractmethod
    def source_units(self, extension: str, content: bytes) -> list[SourceUnit]: ...
    @abstractmethod
    def candidates(self, units: list[SourceUnit]) -> tuple[list[RequirementCandidate], int]: ...

def _normalized(text:str)->str:return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",text.lower())).strip()
def _first_rule(text:str,rules):
    for value,signals in rules:
        if any(signal in text for signal in signals):return value
    return None

class RuleBasedRequirementExtractionProvider(RequirementExtractionProvider):
    def source_units(self,extension:str,content:bytes)->list[SourceUnit]:
        extension=extension.lower()
        if extension=="pdf":return [SourceUnit(page.extract_text() or "",index) for index,page in enumerate(PdfReader(io.BytesIO(content)).pages,1)]
        if extension=="txt":return [SourceUnit(content.decode("utf-8",errors="ignore"))]
        if extension=="docx":
            document=DocxDocument(io.BytesIO(content));units=[];heading=None
            for paragraph in document.paragraphs:
                text=paragraph.text.strip()
                if not text:continue
                if paragraph.style and paragraph.style.name.lower().startswith("heading"):heading=text
                else:units.append(SourceUnit(text,section=heading))
            return units
        return []
    def candidates(self,units:list[SourceUnit])->tuple[list[RequirementCandidate],int]:
        found=[];low=0;seen=set()
        for unit in units:
            heading=unit.section
            for raw_line in unit.text.splitlines():
                line=raw_line.strip()
                if not line:continue
                if HEADING_RE.match(line) or (len(line)<120 and line.isupper()):heading=line;continue
                for excerpt in re.split(r"(?<=[.!?;])\s+",line):
                    excerpt=excerpt.strip()[:2000];lower=excerpt.lower();normalized=_normalized(excerpt)
                    if len(normalized)<25 or any(x in lower for x in NEGATIVE) or normalized.isdigit() or normalized in seen:continue
                    seen.add(normalized);strong=sum(phrase in lower for phrase in STRONG_PHRASES);actor=any(x in lower for x in ACTORS)
                    if not strong and not actor:continue
                    category=_first_rule(lower,CATEGORY_RULES) or "Other";requirement_type=_first_rule(f" {lower} ",TYPE_RULES)
                    clause_match=CLAUSE_RE.match(excerpt);clause=clause_match.group(1) if clause_match else None
                    score=.40+min(.25,strong*.12)+(.12 if actor else 0)+(.08 if category!="Other" else 0)+(.05 if unit.page else 0)+(.04 if clause or heading else 0)
                    if len(excerpt)<45:score-=.12
                    confidence=round(max(0,min(.98,score)),2)
                    if confidence<MIN_CONFIDENCE:low+=1;continue
                    critical=any(x in lower for x in ("bid shall be rejected","disqualification","tender submission deadline"));high=any(x in lower for x in ("bid security","performance security","mandatory qualification","mandatory certificate","statutory permit","completion period"))
                    found.append(RequirementCandidate(excerpt,unit.page,clause,heading,category,requirement_type,confidence,"Critical" if critical else "High" if high else "Medium",strong>0 or actor))
        return found,low

def extract_requirements_from_document(db:Session,document:BidDocument,storage:StorageProvider,user_id:int,request_metadata:dict|None=None)->ExtractionSummary:
    if document.duplicate_of_document_id or not document.storage_path:raise ValueError("Document content is not available for requirement extraction")
    provider=RuleBasedRequirementExtractionProvider();units=provider.source_units(document.file_extension,storage.read(document.storage_path));candidates,low=provider.candidates(units)
    existing=db.scalars(select(BidRequirement).where(BidRequirement.bid_project_id==document.bid_project_id,BidRequirement.source_document_id==document.id)).all()
    signatures={(_normalized(item.requirement_text),item.source_page or "",item.source_clause or "") for item in existing};created=duplicates=0
    for candidate in candidates:
        signature=(_normalized(candidate.text),str(candidate.page or ""),candidate.clause or "")
        if signature in signatures:duplicates+=1;continue
        requirement=BidRequirement(bid_project_id=document.bid_project_id,source_document_id=document.id,requirement_category=candidate.category,requirement_type=candidate.requirement_type,requirement_title=candidate.text[:297]+("..." if len(candidate.text)>297 else ""),requirement_text=candidate.text,source_page=str(candidate.page) if candidate.page else None,source_clause=candidate.clause,source_section=candidate.section,source_excerpt=candidate.text,responsible_function=suggest_responsible_function(candidate.category,candidate.text),priority=candidate.priority,requirement_status="Open",is_mandatory=candidate.is_mandatory,compliance_status="Not Assessed",review_status="Not Reviewed",extraction_method="Rule Based",extraction_confidence=Decimal(str(candidate.confidence)),created_by=user_id)
        db.add(requirement);signatures.add(signature);created+=1
    no_text=not any(unit.text.strip() for unit in units)
    summary=ExtractionSummary(document.id,created,duplicates,low,no_text)
    db.add(AuditEvent(user_id=user_id,bid_project_id=document.bid_project_id,event_type="requirement.extraction_completed",entity_type="BidDocument",entity_id=str(document.id),request_metadata=request_metadata or {},details=asdict(summary)))
    db.commit();return summary
