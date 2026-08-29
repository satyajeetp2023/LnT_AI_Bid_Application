from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidRequirement
from app.services.schedule_scope_coverage import schedule_scope_catalog


PHASE_ORDER={
    "Design":10,
    "Approval":20,
    "Procurement / Supply":30,
    "Construction / Installation":40,
    "Testing":50,
    "Commissioning":60,
    "Handover":70,
    "Execution / Other":45,
}
PHASE_SIGNALS=(
    ("Design",("design","engineering","drawing","calculation")),
    ("Approval",("approval","approve","review")),
    ("Procurement / Supply",("procure","procurement","supply","manufacture","fabrication","delivery")),
    ("Construction / Installation",("construct","construction","install","installation","erect","erection","laying","foundation","civil")),
    ("Testing",("test","testing","inspection","fat","sat")),
    ("Commissioning",("commission","commissioning","energization","energisation")),
    ("Handover",("handover","as-built","as built","training","closeout")),
)


def _phase(name:str):
    lower=(name or "").lower()
    for phase,signals in PHASE_SIGNALS:
        if any(x in lower for x in signals):return phase
    return "Execution / Other"


def build_schedule_skeleton(db:Session,bid_id:int):
    catalog=schedule_scope_catalog(db,bid_id)
    groups=catalog.get("groups",[])
    activities=[]
    for index,group in enumerate(groups,1):
        phase=_phase(group.get("activity_name") or "")
        wbs=group.get("parent_activity_name") or (
            "Tender / BOQ Scope" if group.get("source_type") in {"BOQ","Contract / Technical Requirement","Manual"}
            else "Project-Type Knowledge"
        )
        activities.append({
            "kind":"Activity",
            "suggested_code":f"SCH-{index:04d}",
            "activity_name":group.get("activity_name"),
            "wbs":wbs,
            "phase":phase,
            "phase_rank":PHASE_ORDER.get(phase,45),
            "mandatory":bool(group.get("mandatory")),
            "source_type":group.get("source_type"),
            "source_reference":group.get("source_reference"),
            "authority_score":group.get("authority_score"),
            "evidence_strength":group.get("evidence_strength"),
            "duration":None,
            "calendar":None,
            "resources":None,
            "predecessor_suggestion":None,
            "planning_status":"Needs Planning Input",
        })

    milestones=db.scalars(select(BidRequirement).where(
        BidRequirement.bid_project_id==bid_id,
        BidRequirement.requirement_type=="Milestone",
        BidRequirement.requirement_status.notin_(["Closed","Not Applicable"]),
    )).all()
    for milestone in milestones:
        activities.append({
            "kind":"Milestone",
            "suggested_code":f"MIL-{milestone.id:04d}",
            "activity_name":milestone.requirement_title,
            "wbs":"Contract Milestones",
            "phase":"Milestone",
            "phase_rank":999,
            "mandatory":milestone.is_mandatory,
            "source_type":"Contract Milestone",
            "source_reference":milestone.source_clause or milestone.source_section,
            "authority_score":100 if milestone.is_mandatory else 80,
            "evidence_strength":"Contractual / BOQ Strong",
            "duration":0,
            "calendar":None,
            "resources":None,
            "predecessor_suggestion":None,
            "planning_status":"Needs Date / Logic Confirmation",
        })

    by_wbs=defaultdict(list)
    for row in activities:
        if row["kind"]=="Activity":by_wbs[row["wbs"]].append(row)
    for rows in by_wbs.values():
        rows.sort(key=lambda x:(x["phase_rank"],x["suggested_code"]))
        previous=None
        for row in rows:
            if previous and row["phase_rank"]>=previous["phase_rank"]:
                row["predecessor_suggestion"]=previous["suggested_code"]
            previous=row

    activities.sort(key=lambda x:(x["wbs"],x["phase_rank"],x["suggested_code"]))
    return {
        "items":activities,
        "summary":{
            "logical_scope_items":len(groups),
            "activities":sum(1 for x in activities if x["kind"]=="Activity"),
            "milestones":sum(1 for x in activities if x["kind"]=="Milestone"),
            "mandatory":sum(1 for x in activities if x["mandatory"]),
            "needs_duration":sum(1 for x in activities if x["kind"]=="Activity" and x["duration"] is None),
            "needs_calendar":sum(1 for x in activities if x["kind"]=="Activity" and x["calendar"] is None),
        },
        "version":"phase6-expected-schedule-skeleton-v1",
        "note":"This is a planning skeleton, not a Primavera programme. Durations, calendars, resources and logic must be set and recalculated by the planner.",
    }
