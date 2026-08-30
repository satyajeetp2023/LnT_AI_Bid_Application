import re
from datetime import datetime

from sqlalchemy import or_,select
from sqlalchemy.orm import Session

from app.models import BidRequirement


DATE_PATTERNS=(
    (re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),("%Y-%m-%d",)),
    (re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b"),("%d/%m/%Y","%d-%m-%Y")),
    (re.compile(r"\b(\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})\b",re.I),("%d %B %Y","%d %b %Y")),
)
DURATION_RE=re.compile(r"\b(\d+(?:\.\d+)?)\s*(calendar\s+)?(day|days|month|months|year|years)\b",re.I)
COMPLETION_SIGNALS=("completion period","time for completion","complete within","completion within","contract period","overall duration","project duration")
STOP={"the","and","for","shall","must","within","from","date","completion","period","milestone","project","contract","days","months","years","calendar","activity","schedule"}


def _date(value):
    if not value:return None
    text=str(value).strip()
    for _,formats in DATE_PATTERNS:
        for fmt in formats:
            try:return datetime.strptime(text,fmt)
            except ValueError:pass
    try:return datetime.fromisoformat(text)
    except ValueError:return None


def _extract_date(text:str):
    for pattern,formats in DATE_PATTERNS:
        match=pattern.search(text)
        if not match:continue
        raw=match.group(1)
        for fmt in formats:
            try:return datetime.strptime(raw,fmt),raw
            except ValueError:pass
    return None,None


def _duration_days(text:str):
    lower=text.lower()
    if not any(signal in lower for signal in COMPLETION_SIGNALS):return None,None
    match=DURATION_RE.search(text)
    if not match:return None,None
    value=float(match.group(1));unit=match.group(3).lower()
    if unit.startswith("month"):days=value*30.4375
    elif unit.startswith("year"):days=value*365.25
    else:days=value
    return round(days,2),match.group(0)


def _terms(text:str):
    return {x for x in re.findall(r"[a-z0-9]+",text.lower()) if len(x)>2 and x not in STOP}


def _milestone_match(requirement:BidRequirement,milestones:list[dict]):
    target=_terms(f"{requirement.requirement_title} {requirement.requirement_text}")
    best=None;best_score=0.0
    for milestone in milestones:
        words=_terms(f'{milestone.get("task_code") or ""} {milestone.get("task_name") or ""}')
        if not words:continue
        overlap=len(target&words)
        score=overlap/max(1,min(len(target),len(words)))
        if score>best_score:
            best=milestone;best_score=score
    if best and best_score>=.35:return best,round(best_score,2)
    return None,round(best_score,2)


def align_schedule_to_requirements(db:Session,bid_id:int,analysis:dict):
    requirements=db.scalars(select(BidRequirement).where(
        BidRequirement.bid_project_id==bid_id,
        or_(
            BidRequirement.requirement_category=="Planning / Scheduling Requirement",
            BidRequirement.requirement_type.in_(["Schedule","Milestone"]),
        ),
        BidRequirement.requirement_status.notin_(["Closed","Not Applicable"]),
    ).order_by(BidRequirement.priority,BidRequirement.id)).all()

    checks=[]
    milestones=analysis.get("milestones",[])
    planned_days=analysis.get("project",{}).get("planned_duration_days")

    for req in requirements:
        text=f"{req.requirement_title} {req.requirement_text}"
        lower=text.lower()
        resource_required=any(x in lower for x in ("resource loaded","resource-loaded","resource loading","manpower histogram","equipment histogram","labour histogram","labor histogram"))
        if resource_required:
            loading=(analysis.get("optimization_advisor") or {}).get("resource_loading") or {}
            status=loading.get("status") or "Unknown"
            ratio=loading.get("coverage_ratio")
            if status=="Not Resource Loaded":
                check_status="Fail";reason="Tender requires resource-loaded planning output, but the XER contains no resource assignments."
            elif status=="Partially Resource Loaded":
                check_status="Manual Review";reason="Resource assignments exist only for part of the schedule; confirm whether this satisfies the tender requirement."
            elif status=="Broadly Resource Loaded":
                check_status="Pass";reason="The schedule is broadly resource loaded."
            else:
                check_status="Manual Review";reason="Resource-loading status could not be established."
            checks.append({
                "requirement_id":req.id,"requirement_title":req.requirement_title,"source_clause":req.source_clause,
                "check_type":"Resource Loading","expected":"Resource-loaded schedule / histogram requirement",
                "actual":f'{status}' + (f' · {round(float(ratio)*100)}% activity coverage' if ratio is not None else ""),
                "status":check_status,"confidence":.95,"reason":reason,
            })
            continue
        expected_days,raw_duration=_duration_days(text)
        required_date,raw_date=_extract_date(text)

        if expected_days is not None:
            if planned_days is None:
                status="Manual Review";actual=None;reason="The XER does not expose a usable planned project start/finish pair."
            else:
                status="Pass" if planned_days<=expected_days+1 else "Fail"
                actual=f"{planned_days:.1f} days"
                reason="Planned project duration is within the extracted completion period." if status=="Pass" else "Planned project duration exceeds the extracted completion period."
            checks.append({
                "requirement_id":req.id,"requirement_title":req.requirement_title,"source_clause":req.source_clause,
                "check_type":"Completion Duration","expected":raw_duration,"actual":actual,
                "status":status,"confidence":.92,"reason":reason,
            })
            continue

        is_milestone=(req.requirement_type=="Milestone" or "milestone" in text.lower())
        if required_date and is_milestone:
            milestone,match_confidence=_milestone_match(req,milestones)
            if not milestone:
                checks.append({
                    "requirement_id":req.id,"requirement_title":req.requirement_title,"source_clause":req.source_clause,
                    "check_type":"Dated Milestone","expected":raw_date,"actual":None,
                    "status":"Manual Review","confidence":match_confidence,
                    "reason":"A dated milestone requirement was found, but no schedule milestone could be matched reliably.",
                })
                continue
            actual_date=_date(milestone.get("finish_date"))
            if not actual_date:
                status="Manual Review";reason="The matched schedule milestone has no usable finish date."
            else:
                status="Pass" if actual_date.date()<=required_date.date() else "Fail"
                reason="Matched schedule milestone is on/before the required date." if status=="Pass" else "Matched schedule milestone is later than the required date."
            checks.append({
                "requirement_id":req.id,"requirement_title":req.requirement_title,"source_clause":req.source_clause,
                "check_type":"Dated Milestone","expected":raw_date,
                "actual":f'{milestone.get("task_code") or ""} · {milestone.get("task_name") or ""} · {milestone.get("finish_date") or "No date"}',
                "status":status,"confidence":match_confidence,"reason":reason,
                "matched_task_id":milestone.get("task_id"),
            })
            continue

        checks.append({
            "requirement_id":req.id,"requirement_title":req.requirement_title,"source_clause":req.source_clause,
            "check_type":"Schedule Requirement","expected":None,"actual":None,
            "status":"Manual Review","confidence":.0,
            "reason":"The requirement is schedule-related but does not contain a safely machine-checkable completion duration or dated milestone.",
        })

    passed=sum(1 for x in checks if x["status"]=="Pass")
    failed=sum(1 for x in checks if x["status"]=="Fail")
    manual=sum(1 for x in checks if x["status"]=="Manual Review")
    grade="Misaligned" if failed else "Needs Review" if manual else "Aligned"
    return {
        "grade":grade,
        "checks":checks,
        "summary":{
            "schedule_requirements":len(checks),
            "automatically_checked":passed+failed,
            "passed":passed,
            "failed":failed,
            "manual_review":manual,
        },
        "version":"phase6-schedule-requirement-alignment-v2",
        "note":"Only explicit completion-duration and reliably matched dated-milestone requirements are checked automatically.",
    }
