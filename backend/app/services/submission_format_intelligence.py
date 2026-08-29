import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidRequirement


FORMAT_SIGNALS=(
    ("Form", re.compile(r"\bform\s+[A-Za-z0-9.-]+",re.I)),
    ("Annexure", re.compile(r"\bannex(?:ure|ure)\s*[-:]?\s*[A-Za-z0-9.-]+",re.I)),
    ("Schedule", re.compile(r"\bschedule\s*[-:]?\s*[A-Za-z0-9.-]+",re.I)),
    ("Appendix", re.compile(r"\bappendix\s*[-:]?\s*[A-Za-z0-9.-]+",re.I)),
    ("Format", re.compile(r"\b(?:prescribed|specified|given)\s+format\b",re.I)),
)
SUBMISSION_WORDS=("submit","submission","furnish","provide","attach","enclose","upload","bidder shall")
FORMAT_WORDS=("form","format","annexure","schedule","appendix","template","proforma")


def _format_name(text:str)->tuple[str,str]:
    for kind,pattern in FORMAT_SIGNALS:
        match=pattern.search(text)
        if match:return kind,match.group(0).strip(" .,:;")
    return "Format","Employer-prescribed submission format"


def detect_submission_formats(db:Session,bid_id:int):
    rows=db.scalars(select(BidRequirement).where(BidRequirement.bid_project_id==bid_id).order_by(BidRequirement.id)).all()
    items=[]
    seen=set()
    for r in rows:
        text=f"{r.requirement_title} {r.requirement_text} {r.source_excerpt or ''}"
        lower=text.lower()
        has_format=r.requirement_type=="Form / Format" or any(word in lower for word in FORMAT_WORDS)
        has_submission=r.requirement_category in {"Submission Requirement","Documentation Requirement"} or any(word in lower for word in SUBMISSION_WORDS)
        if not (has_format and has_submission):continue
        kind,name=_format_name(text)
        key=(name.lower(),r.source_document_id,r.source_clause or "",r.source_page or "")
        if key in seen:continue
        seen.add(key)
        confidence=.94 if r.requirement_type=="Form / Format" else .88 if any(x in lower for x in ("annexure","appendix","schedule","form ")) else .78
        items.append({
            "requirement_id":r.id,
            "format_kind":kind,
            "format_name":name,
            "requirement_title":r.requirement_title,
            "requirement_text":r.requirement_text,
            "responsible_function":r.responsible_function,
            "priority":r.priority,
            "mandatory":r.is_mandatory,
            "source_document_id":r.source_document_id,
            "source_document":r.source_document_title or r.source_original_filename,
            "source_page":r.source_page,
            "source_clause":r.source_clause,
            "source_section":r.source_section,
            "source_excerpt":r.source_excerpt,
            "confidence":confidence,
            "status":"Detected",
            "next_action":"Review the source requirement and locate the employer-provided blank template or prescribed layout.",
        })
    items.sort(key=lambda x:(0 if x["mandatory"] else 1,0 if x["priority"]=="Critical" else 1,x["format_name"].lower()))
    return {
        "items":items,
        "summary":{
            "detected":len(items),
            "mandatory":sum(1 for x in items if x["mandatory"]),
            "high_priority":sum(1 for x in items if x["priority"] in {"Critical","High"}),
            "with_source":sum(1 for x in items if x["source_document_id"] is not None),
        },
        "version":"phase5-submission-format-intelligence-v1",
    }
