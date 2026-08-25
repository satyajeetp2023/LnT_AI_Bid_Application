import io
import logging
import re
from dataclasses import dataclass
from decimal import Decimal

from docx import Document as DocxDocument
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.models import AuditEvent, BidDocument
from app.services.intelligence import DocumentIntelligenceProvider
from app.services.document_taxonomy import DOCUMENT_CATEGORIES
from app.storage.base import StorageProvider

CLASSIFIER_VERSION = "phase1-rule-v1"
logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ClassificationRule:
    category: str
    signals: tuple[tuple[str, float], ...]
    types: tuple[tuple[str, str], ...] = ()

@dataclass(frozen=True)
class ClassificationResult:
    category: str | None
    document_type: str | None
    confidence: float | None
    status: str

RULES = (
    ClassificationRule("Notice / Invitation", (("notice inviting tender", .34), ("invitation for bids", .34), ("invitation to bid", .34), ("nit", .24), ("ifb", .24), ("request for proposal", .28)), (("nit", "NIT"), ("ifb", "IFB"), ("request for proposal", "RFP"))),
    ClassificationRule("Instructions to Bidders", (("instructions to bidders", .42), ("instruction to bidders", .38), ("itb", .24))),
    ClassificationRule("Bid Data Sheet", (("bid data sheet", .44), ("bds", .25))),
    ClassificationRule("Conditions of Contract", (("general conditions of contract", .38), ("particular conditions of contract", .38), ("special conditions of contract", .38), ("conditions of contract", .28), ("gcc", .24), ("pcc", .24), ("scc", .24)), (("gcc", "GCC"), ("pcc", "PCC"), ("scc", "SCC"))),
    ClassificationRule("Employer's Requirements", (("employer's requirements", .44), ("employer requirements", .42))),
    ClassificationRule("Technical Specifications", (("technical specifications", .42), ("technical specification", .40), ("technical requirements", .34), ("specification", .16))),
    ClassificationRule("BOQ / Price Schedule", (("bill of quantities", .44), ("boq", .30), ("price schedule", .38), ("schedule of prices", .38), ("schedule of rates", .38)), (("bill of quantities", "BOQ"), ("boq", "BOQ"), ("price schedule", "Price Schedule"), ("schedule of rates", "Schedule of Rates"))),
    ClassificationRule("Drawings", (("drawings", .32), ("drawing", .25), ("layout", .20), ("schematic", .24))),
    ClassificationRule("Forms / Formats / Schedules", (("form of bid", .36), ("bid form", .34), ("schedule", .14), ("format", .18), ("annexure", .20), ("appendix", .18))),
    ClassificationRule("Qualification Requirements", (("qualification requirements", .42), ("eligibility criteria", .36), ("experience requirements", .34), ("financial capacity", .34))),
    ClassificationRule("Evaluation Criteria", (("evaluation criteria", .42), ("evaluation methodology", .38), ("technical evaluation", .32), ("financial evaluation", .32))),
    ClassificationRule("Scope of Work", (("scope of work", .44), ("scope of supply", .40), ("scope of services", .40))),
    ClassificationRule("Addendum / Corrigendum", (("corrigendum", .42), ("addendum", .42), ("amendment", .32)), (("corrigendum", "Corrigendum"), ("addendum", "Addendum"), ("amendment", "Amendment"))),
    ClassificationRule("Pre-Bid Clarification", (("pre-bid", .34), ("prebid", .32), ("response to queries", .38), ("prebid queries", .40), ("clarification", .24))),
    ClassificationRule("Reference Document", (("reference information", .36), ("reference document", .36), ("feasibility report", .38), ("dpr", .25), ("geotechnical report", .40))),
)

def _contains(value: str, phrase: str) -> bool:
    if len(phrase) <= 4 and phrase.isalnum():
        return bool(re.search(rf"\b{re.escape(phrase)}\b", value))
    return phrase in value

def extract_text(extension: str, content: bytes) -> str:
    extension = extension.lower()
    if extension == "txt":
        return content.decode("utf-8", errors="ignore")
    if extension == "pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
    if extension == "docx":
        document = DocxDocument(io.BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    return ""

def classify_content(filename: str, text: str) -> ClassificationResult:
    normalized_name = re.sub(r"[_\-.]+", " ", filename.lower())
    normalized_text = re.sub(r"\s+", " ", text.lower())[:250_000]
    ranked: list[tuple[float, ClassificationRule, int, int]] = []
    for rule in RULES:
        filename_hits = [weight for phrase, weight in rule.signals if _contains(normalized_name, phrase)]
        text_hits = [weight for phrase, weight in rule.signals if _contains(normalized_text, phrase)]
        filename_score = min(.42, sum(filename_hits) * .90)
        text_score = min(.62, sum(text_hits))
        corroboration = .10 if filename_hits and text_hits else .0
        diversity = min(.12, max(0, len(text_hits) - 1) * .06)
        ranked.append((min(.98, filename_score + text_score + corroboration + diversity), rule, len(filename_hits), len(text_hits)))
    score, rule, filename_hit_count, text_hit_count = max(ranked, key=lambda item: item[0])
    runner_up = sorted((item[0] for item in ranked), reverse=True)[1]
    if score < .35 or score - runner_up < .08:
        return ClassificationResult(None, None, round(score, 2) if score else None, "needs_review")
    status = "classified" if score >= .80 else "needs_review"
    combined = f"{normalized_name} {normalized_text}"
    document_type = None
    if score >= .50:
        for phrase, type_name in rule.types:
            if _contains(combined, phrase):
                document_type = type_name
                break
    return ClassificationResult(rule.category, document_type, round(max(0.0, min(1.0, score)), 2), status)

class RuleBasedDocumentIntelligenceProvider(DocumentIntelligenceProvider):
    version = CLASSIFIER_VERSION

    def classify(self, filename: str, extension: str, content: bytes) -> ClassificationResult:
        text = extract_text(extension, content)
        return classify_content(filename, text)

def auto_classify_document(db: Session, document: BidDocument, storage: StorageProvider, user_id: int, *, force: bool = False, request_metadata: dict | None = None) -> BidDocument:
    if document.classification_status == "manually_classified" and not force:
        raise ValueError("Manual classification must not be overwritten")
    if not document.storage_path:
        return document
    provider = RuleBasedDocumentIntelligenceProvider()
    try:
        result = provider.classify(document.original_filename, document.file_extension, storage.read(document.storage_path))
        document.document_category = result.category
        document.document_type = result.document_type
        document.classification_confidence = Decimal(str(result.confidence)) if result.confidence is not None else None
        document.classification_status = result.status
        document.document_status = "Uploaded" if result.status == "classified" else "Needs Review"
        details = {"predicted_category": result.category, "predicted_type": result.document_type, "confidence": result.confidence, "classification_status": result.status, "classifier_version": provider.version, "forced": force}
        event_type = "document.auto_classified"
    except Exception as exc:
        logger.warning("Document auto-classification failed for document %s: %s", document.id, type(exc).__name__)
        document.document_category = None
        document.document_type = None
        document.classification_status = "needs_review"
        document.classification_confidence = None
        document.document_status = "Needs Review"
        details = {"predicted_category": None, "predicted_type": None, "confidence": None, "classification_status": "needs_review", "classifier_version": provider.version, "forced": force, "failure_reason": type(exc).__name__}
        event_type = "document.auto_classification_failed"
    db.add(AuditEvent(user_id=user_id, bid_project_id=document.bid_project_id, event_type=event_type, entity_type="BidDocument", entity_id=str(document.id), request_metadata=request_metadata or {}, details=details))
    db.commit()
    return document
