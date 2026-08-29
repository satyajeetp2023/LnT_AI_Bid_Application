from collections import Counter
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidMissingInput,BidRequirement
from app.services.missing_input_taxonomy import RESOLVED_STATUSES
from app.services.responsibility_assignment import suggest_responsible_function


def calculate_estimation_readiness(db:Session,bid_id:int):
    requirements=db.scalars(select(BidRequirement).where(
        BidRequirement.bid_project_id==bid_id,
        BidRequirement.requirement_status.notin_(["Closed","Not Applicable"]),
    )).all()
    gaps=db.scalars(select(BidMissingInput).where(
        BidMissingInput.bid_project_id==bid_id,
        BidMissingInput.status.notin_(RESOLVED_STATUSES),
    )).all()

    total=len(requirements)
    req_ids={r.id for r in requirements}
    blocked_ids={g.requirement_id for g in gaps if g.requirement_id in req_ids}
    info_complete=max(0,total-len(blocked_ids))

    reviewed=sum(1 for r in requirements if r.review_status!="Not Reviewed")
    compliance_assessed=sum(1 for r in requirements if r.compliance_status!="Not Assessed")
    critical_open=sum(1 for g in gaps if g.priority=="Critical")
    high_open=sum(1 for g in gaps if g.priority=="High")
    overdue=sum(1 for g in gaps if g.required_by_date and g.required_by_date<date.today())

    def pct(value:int)->float:
        return 100.0 if total==0 else round(value*100/total,1)

    information_score=pct(info_complete)
    review_score=pct(reviewed)
    compliance_score=pct(compliance_assessed)
    blocker_score=max(0.0,round(100-(critical_open*12+high_open*6+max(0,len(gaps)-critical_open-high_open)*2),1))
    overall=round(information_score*.45+review_score*.25+compliance_score*.20+blocker_score*.10,1)

    existing_gap_req_ids={g.requirement_id for g in gaps if g.requirement_id is not None}
    candidates=[]
    for r in requirements:
        if r.review_status!="Needs Clarification" or r.id in existing_gap_req_ids:continue
        candidates.append({
            "requirement_id":r.id,
            "title":r.requirement_title,
            "category":r.requirement_category,
            "priority":r.priority,
            "responsible_function":r.responsible_function or suggest_responsible_function(r.requirement_category,r.requirement_text),
            "source_document":r.source_document_title or r.source_original_filename,
            "source_page":r.source_page,
            "source_clause":r.source_clause,
            "reason":"Requirement has been reviewed and marked Needs Clarification, but no unresolved Missing Input is linked to it.",
        })
    candidates.sort(key=lambda x:({"Critical":0,"High":1,"Medium":2,"Low":3}.get(x["priority"],4),x["title"].lower()))

    by_function=Counter((g.responsible_function or "Unassigned") for g in gaps)
    by_category=Counter(g.input_category for g in gaps)

    return {
        "overall_score":overall,
        "grade":"Ready" if overall>=85 else "Needs Attention" if overall>=65 else "Not Ready",
        "components":{
            "information_completeness":information_score,
            "review_completion":review_score,
            "compliance_assessment":compliance_score,
            "blocker_control":blocker_score,
        },
        "counts":{
            "active_requirements":total,
            "requirements_with_open_gaps":len(blocked_ids),
            "open_missing_inputs":len(gaps),
            "critical_open":critical_open,
            "high_open":high_open,
            "overdue":overdue,
            "candidate_gaps":len(candidates),
        },
        "candidate_gaps":candidates,
        "open_gaps_by_function":[{"name":k,"count":v} for k,v in by_function.most_common()],
        "open_gaps_by_category":[{"name":k,"count":v} for k,v in by_category.most_common()],
        "methodology":{
            "information_completeness_weight":45,
            "review_completion_weight":25,
            "compliance_assessment_weight":20,
            "blocker_control_weight":10,
            "version":"phase3-readiness-rule-v2",
        },
    }
