import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidDocument,BidRequirement


FORMAT_SIGNALS=(
    ("Form", re.compile(r"\bform\s+[A-Za-z0-9.-]+",re.I)),
    ("Annexure", re.compile(r"\bannex(?:ure|ure)\s*[-:]?\s*[A-Za-z0-9.-]+",re.I)),
    ("Schedule", re.compile(r"\bschedule\s*[-:]?\s*[A-Za-z0-9.-]+",re.I)),
    ("Appendix", re.compile(r"\bappendix\s*[-:]?\s*[A-Za-z0-9.-]+",re.I)),
    ("Format", re.compile(r"\b(?:prescribed|specified|given)\s+format\b",re.I)),
)
SUBMISSION_WORDS=("submit","submission","furnish","provide","attach","enclose","upload","bidder shall")
FORMAT_WORDS=("form","format","annexure","schedule","appendix","template","proforma")


def _terms(text:str)->set[str]:
    return {x for x in re.findall(r"[a-z0-9]+",text.lower()) if len(x)>1 and x not in {"the","and","for","with","form","format","annexure","schedule","appendix"}}


def _locate_template(documents:list[BidDocument],kind:str,name:str,requirement_text:str):
    target=_terms(f"{name} {requirement_text}")
    best=None;best_score=0.0
    for doc in documents:
        label=f"{doc.document_title or ''} {doc.original_filename or ''} {doc.document_type or ''}"
        lower=label.lower()
        doc_terms=_terms(label)
        overlap=len(target&doc_terms)
        score=overlap/max(1,len(target))
        if kind.lower() in lower:score+=.20
        if name.lower() in lower:score+=.35
        score=min(1.0,score)
        if score>best_score:
            best=doc;best_score=score
    if best and best_score>=.45:return best,round(best_score,2)
    return None,0.0


def _format_name(text:str)->tuple[str,str]:
    for kind,pattern in FORMAT_SIGNALS:
        match=pattern.search(text)
        if match:return kind,match.group(0).strip(" .,:;")
    return "Format","Employer-prescribed submission format"


def detect_submission_formats(db:Session,bid_id:int):
    rows=db.scalars(select(BidRequirement).where(BidRequirement.bid_project_id==bid_id).order_by(BidRequirement.id)).all()
    documents=db.scalars(select(BidDocument).where(BidDocument.bid_project_id==bid_id,BidDocument.document_status!="Archived")).all()
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
        template,template_confidence=_locate_template(documents,kind,name,r.requirement_text)
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
            "template_document_id":template.id if template else None,
            "template_document":(template.document_title or template.original_filename) if template else None,
            "template_match_confidence":template_confidence,
            "status":"Template Located" if template else "Template Missing",
            "next_action":"Review the located employer template and confirm the required fields before controlled population." if template else "Locate or obtain the employer-provided blank template / prescribed layout before preparing the submission.",
        })
    items.sort(key=lambda x:(0 if x["mandatory"] else 1,0 if x["priority"]=="Critical" else 1,x["format_name"].lower()))
    return {
        "items":items,
        "summary":{
            "detected":len(items),
            "mandatory":sum(1 for x in items if x["mandatory"]),
            "high_priority":sum(1 for x in items if x["priority"] in {"Critical","High"}),
            "with_source":sum(1 for x in items if x["source_document_id"] is not None),
            "template_located":sum(1 for x in items if x["template_document_id"] is not None),
            "template_missing":sum(1 for x in items if x["template_document_id"] is None),
        },
        "version":"phase5-submission-format-intelligence-v2",
    }
