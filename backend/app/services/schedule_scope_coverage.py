import re
from collections import defaultdict
from datetime import datetime,timezone
from decimal import Decimal
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent,BidProject,BidRequirement,ScheduleScopeItem
from app.services.project_type_activity_library import project_type_activity_library
from app.services.p6_xer import parse_xer


SCOPE_CATEGORIES={
    "Technical Requirement","Planning / Scheduling Requirement","Design Requirement",
    "Procurement Requirement","Construction Requirement","Testing & Commissioning Requirement",
    "Interface Requirement","Quality Requirement","Safety Requirement",
}
ACTION_RE=re.compile(
    r"\b(?:shall|must|required to|is to)\s+(?:be\s+)?"
    r"(?:design|prepare|procure|manufacture|supply|deliver|construct|install|erect|lay|test|commission|integrate|inspect|approve|complete|execute|provide)\s+(.+)",
    re.I,
)
STOP={
    "the","and","for","with","shall","must","required","contractor","bidder","tenderer","employer",
    "work","works","project","system","systems","including","all","any","this","that","from","into",
}
LIFECYCLE_STAGES=(
    ("Design",("design","engineering","drawings","calculation")),
    ("Approval",("approval","approve","review")),
    ("Procurement / Supply",("procure","procurement","supply","manufacture","fabricate","deliver")),
    ("Construction / Installation",("construct","construction","install","installation","erect","erection","lay","laying")),
    ("Testing",("test","testing","inspection")),
    ("Commissioning",("commission","commissioning","energize","energisation","energization")),
)


def _lifecycle_stages(text:str):
    lower=str(text or "").lower()
    return [stage for stage,signals in LIFECYCLE_STAGES if any(signal in lower for signal in signals)]




def _terms(text:str)->set[str]:
    return {x for x in re.findall(r"[a-z0-9]+",str(text or "").lower()) if len(x)>2 and x not in STOP}


def _activity_name(requirement:BidRequirement)->str:
    text=re.sub(r"\s+"," ",requirement.requirement_text).strip()
    match=ACTION_RE.search(text)
    candidate=match.group(1) if match else requirement.requirement_title
    candidate=re.split(r"[.;]",candidate,1)[0].strip(" :-")
    if len(candidate)>180:candidate=candidate[:177]+"..."
    return candidate or requirement.requirement_title[:180]


def _keywords(name:str,text:str)->list[str]:
    words=_terms(f"{name} {text}")
    return sorted(words)[:30]


def _scope_item_dict(item:ScheduleScopeItem):
    return {
        "id":item.id,
        "bid_project_id":item.bid_project_id,
        "parent_id":item.parent_id,
        "source_requirement_id":item.source_requirement_id,
        "source_document_id":item.source_document_id,
        "activity_name":item.activity_name,
        "activity_level":item.activity_level,
        "source_type":item.source_type,
        "source_reference":item.source_reference,
        "source_excerpt":item.source_excerpt,
        "mandatory":item.mandatory,
        "match_keywords":item.match_keywords or [],
        "coverage_status":item.coverage_status,
        "matched_task_code":item.matched_task_code,
        "matched_task_name":item.matched_task_name,
        "match_confidence":float(item.match_confidence) if item.match_confidence is not None else None,
        "disposition_status":item.disposition_status,
        "disposition_reason":item.disposition_reason,
        "disposition_by":item.disposition_by,
        "disposition_at":item.disposition_at,
        "blocking":_is_blocking(item),
        "why_expected":item.source_excerpt or (
            f"Expected from {item.source_type}" + (f" · {item.source_reference}" if item.source_reference else "")
        ),
        "why_flagged":(
            "No sufficiently similar schedule activity was found."
            if item.coverage_status=="Missing" else
            "A possible schedule activity was found, but the match is not strong enough to confirm automatically."
            if item.coverage_status=="Possible Match" else
            "A sufficiently strong schedule match was found."
            if item.coverage_status=="Covered" else
            "Coverage has not yet been evaluated."
        ),
    }


def _is_blocking(item:ScheduleScopeItem)->bool:
    if not item.mandatory:return False
    if item.coverage_status=="Covered":return False
    if item.coverage_status=="Possible Match":
        return item.disposition_status!="Confirmed Covered"
    if item.coverage_status=="Missing":
        return item.disposition_status in {"Unexplained","To Be Added"}
    return True


def sync_scope_from_project_type(db:Session,bid_id:int,user_id:int):
    project=db.get(BidProject,bid_id)
    if not project:return {"created":0,"updated":0}
    templates=project_type_activity_library(project.project_type)
    existing=db.scalars(select(ScheduleScopeItem).where(
        ScheduleScopeItem.bid_project_id==bid_id,
        ScheduleScopeItem.source_type=="Project-Type Knowledge",
    )).all()
    by_ref={(x.source_reference or "",x.activity_name.lower()):x for x in existing}
    created=updated=0
    for template in templates:
        key=(project.project_type,template.activity.lower())
        parent=by_ref.get(key)
        if not parent:
            parent=ScheduleScopeItem(
                bid_project_id=bid_id,
                activity_name=template.activity,
                activity_level="Activity Family",
                source_type="Project-Type Knowledge",
                source_reference=project.project_type,
                source_excerpt=f"Suggested from project-type library with confidence {template.confidence:.2f}.",
                mandatory=False,
                match_keywords=sorted(set(template.keywords)|_terms(template.activity)),
                created_by=user_id,
            )
            db.add(parent);db.flush();created+=1
            by_ref[key]=parent
        else:
            parent.match_keywords=sorted(set(template.keywords)|_terms(template.activity))
            updated+=1
        for subactivity in template.subactivities:
            child_key=(parent.id,subactivity.lower())
            child=db.scalar(select(ScheduleScopeItem).where(
                ScheduleScopeItem.bid_project_id==bid_id,
                ScheduleScopeItem.parent_id==parent.id,
                ScheduleScopeItem.source_type=="Project-Type Knowledge",
                ScheduleScopeItem.activity_name==subactivity,
            ))
            if child:continue
            db.add(ScheduleScopeItem(
                bid_project_id=bid_id,
                parent_id=parent.id,
                activity_name=subactivity,
                activity_level="Sub-Activity",
                source_type="Project-Type Knowledge",
                source_reference=project.project_type,
                source_excerpt=f"Suggested child activity under {template.activity}.",
                mandatory=False,
                match_keywords=_keywords(subactivity," ".join(template.keywords)),
                created_by=user_id,
            ));created+=1
    db.flush()
    return {"created":created,"updated":updated}


def sync_scope_from_requirements(db:Session,bid_id:int,user_id:int,request_metadata:dict|None=None):
    project_sync=sync_scope_from_project_type(db,bid_id,user_id)
    requirements=db.scalars(select(BidRequirement).where(
        BidRequirement.bid_project_id==bid_id,
        BidRequirement.requirement_category.in_(SCOPE_CATEGORIES),
        BidRequirement.requirement_status.notin_(["Closed","Not Applicable"]),
    )).all()
    existing=db.scalars(select(ScheduleScopeItem).where(
        ScheduleScopeItem.bid_project_id==bid_id,
        ScheduleScopeItem.source_requirement_id.is_not(None),
    )).all()
    by_requirement={x.source_requirement_id:x for x in existing}
    created=updated=0
    for req in requirements:
        name=_activity_name(req)
        words=_keywords(name,req.requirement_text)
        if len(words)<2:continue
        item=by_requirement.get(req.id)
        if item:
            item.activity_name=name
            item.source_document_id=req.source_document_id
            item.source_reference=req.source_clause or req.source_section
            item.source_excerpt=req.requirement_text[:2000]
            item.mandatory=req.is_mandatory
            item.match_keywords=words
            updated+=1
        else:
            item=ScheduleScopeItem(
                bid_project_id=bid_id,
                source_requirement_id=req.id,
                source_document_id=req.source_document_id,
                activity_name=name,
                activity_level="Activity",
                source_type="Contract / Technical Requirement",
                source_reference=req.source_clause or req.source_section,
                source_excerpt=req.requirement_text[:2000],
                mandatory=req.is_mandatory,
                match_keywords=words,
                created_by=user_id,
            )
            db.add(item);db.flush();created+=1
        stages=_lifecycle_stages(req.requirement_text)
        if len(stages)>1:
            for stage in stages:
                child_name=f"{stage}: {name}"
                child=db.scalar(select(ScheduleScopeItem).where(
                    ScheduleScopeItem.bid_project_id==bid_id,
                    ScheduleScopeItem.parent_id==item.id,
                    ScheduleScopeItem.source_requirement_id==req.id,
                    ScheduleScopeItem.activity_name==child_name,
                ))
                if child:continue
                db.add(ScheduleScopeItem(
                    bid_project_id=bid_id,
                    parent_id=item.id,
                    source_requirement_id=req.id,
                    source_document_id=req.source_document_id,
                    activity_name=child_name[:300],
                    activity_level="Sub-Activity",
                    source_type="Contract / Technical Requirement",
                    source_reference=req.source_clause or req.source_section,
                    source_excerpt=req.requirement_text[:2000],
                    mandatory=req.is_mandatory,
                    match_keywords=_keywords(child_name,req.requirement_text),
                    created_by=user_id,
                ));created+=1
    db.add(AuditEvent(
        user_id=user_id,bid_project_id=bid_id,event_type="schedule.scope_catalog_synced",
        entity_type="BidProject",entity_id=str(bid_id),request_metadata=request_metadata or {},
        details={"created":created,"updated":updated,"requirements_considered":len(requirements),"project_type_created":project_sync["created"],"project_type_updated":project_sync["updated"]},
    ))
    db.commit()
    return {"created":created,"updated":updated,"requirements_considered":len(requirements),"project_type":project_sync}


def add_scope_item(
    db:Session,bid_id:int,payload:dict,user_id:int,request_metadata:dict|None=None
):
    name=str(payload.get("activity_name") or "").strip()
    if not name:raise ValueError("activity_name is required")
    source_type=str(payload.get("source_type") or "Manual").strip()
    item=ScheduleScopeItem(
        bid_project_id=bid_id,
        parent_id=payload.get("parent_id"),
        source_document_id=payload.get("source_document_id"),
        activity_name=name,
        activity_level=str(payload.get("activity_level") or "Activity"),
        source_type=source_type,
        source_reference=str(payload.get("source_reference") or "").strip() or None,
        source_excerpt=str(payload.get("source_excerpt") or "").strip() or None,
        mandatory=bool(payload.get("mandatory",True)),
        match_keywords=_keywords(name,str(payload.get("source_excerpt") or "")),
        created_by=user_id,
    )
    db.add(item);db.flush()
    db.add(AuditEvent(
        user_id=user_id,bid_project_id=bid_id,event_type="schedule.scope_item_added",
        entity_type="ScheduleScopeItem",entity_id=str(item.id),request_metadata=request_metadata or {},
        details={"source_type":source_type,"activity_name":name},
    ))
    db.commit();db.refresh(item)
    return _scope_item_dict(item)


def _wbs_paths(rows:list[dict]):
    by_id={x.get("wbs_id"):x for x in rows if x.get("wbs_id")}
    cache={}
    def path(wbs_id):
        if not wbs_id:return ""
        if wbs_id in cache:return cache[wbs_id]
        parts=[];seen=set();current=by_id.get(wbs_id)
        while current and current.get("wbs_id") not in seen:
            seen.add(current.get("wbs_id"))
            label=current.get("wbs_name") or current.get("wbs_short_name") or ""
            if label:parts.append(str(label))
            current=by_id.get(current.get("parent_wbs_id"))
        result=" > ".join(reversed(parts))
        cache[wbs_id]=result
        return result
    return path


def _activity_search_index(tables:dict[str,list[dict]]):
    tasks=tables.get("TASK",[])
    wbs_path=_wbs_paths(tables.get("PROJWBS",[]))
    code_rows={x.get("actv_code_id"):x for x in tables.get("ACTVCODE",[]) if x.get("actv_code_id")}
    type_rows={x.get("actv_code_type_id"):x for x in tables.get("ACTVTYPE",[]) if x.get("actv_code_type_id")}
    task_codes=defaultdict(list)
    for row in tables.get("TASKACTV",[]):
        task_id=row.get("task_id");code=code_rows.get(row.get("actv_code_id")) or {}
        ctype=type_rows.get(code.get("actv_code_type_id")) or {}
        code_label=" ".join(str(x) for x in (
            ctype.get("actv_code_type") or ctype.get("actv_code_type_name") or "",
            code.get("short_name") or code.get("actv_code_name") or code.get("actv_code") or "",
        ) if x)
        if task_id and code_label:task_codes[task_id].append(code_label)

    index=[]
    for task in tasks:
        wbs=wbs_path(task.get("wbs_id"))
        codes=task_codes.get(task.get("task_id"),[])
        task_name=str(task.get("task_name") or "")
        task_code=str(task.get("task_code") or "")
        context=" ".join([task_code,task_name,wbs,*codes])
        index.append({
            "task":task,
            "task_name":task_name,
            "task_code":task_code,
            "wbs_path":wbs,
            "activity_codes":codes,
            "context":context,
            "terms":_terms(context),
        })
    return index


def _match(item:ScheduleScopeItem,index:list[dict]):
    target=_terms(" ".join(item.match_keywords or [])+" "+item.activity_name)
    if not target:return None,0.0,[]
    scored=[]
    for entry in index:
        words=entry["terms"]
        if not words:continue
        matched=sorted(target&words)
        overlap=len(matched)/max(1,len(target))
        task_name=entry["task_name"].lower()
        name_ratio=SequenceMatcher(None,item.activity_name.lower(),task_name).ratio()
        contains=1.0 if item.activity_name.lower() in task_name and task_name else 0.0
        context_bonus=min(.12,len(matched)*.02) if matched else 0.0
        score=min(1.0,max(contains,.62*overlap+.28*name_ratio+context_bonus))
        scored.append({
            "entry":entry,
            "score":round(score,3),
            "matched_terms":matched,
        })
    scored.sort(key=lambda x:(-x["score"],x["entry"]["task_code"]))
    best=scored[0] if scored else None
    candidates=[{
        "task_code":x["entry"]["task_code"] or None,
        "task_name":x["entry"]["task_name"] or None,
        "wbs_path":x["entry"]["wbs_path"] or None,
        "activity_codes":x["entry"]["activity_codes"],
        "score":x["score"],
        "matched_terms":x["matched_terms"],
    } for x in scored[:3] if x["score"]>=.25]
    return (best["entry"]["task"] if best else None),(best["score"] if best else 0.0),candidates


def evaluate_scope_coverage(db:Session,bid_id:int,xer_content:bytes,user_id:int,request_metadata:dict|None=None):
    tables=parse_xer(xer_content)
    tasks=tables.get("TASK",[])
    search_index=_activity_search_index(tables)
    candidate_matches={}
    items=db.scalars(select(ScheduleScopeItem).where(
        ScheduleScopeItem.bid_project_id==bid_id
    ).order_by(ScheduleScopeItem.id)).all()
    for item in items:
        task,confidence,candidates=_match(item,search_index)
        candidate_matches[item.id]=candidates
        previous=item.coverage_status
        if task and confidence>=.72:
            item.coverage_status="Covered"
        elif task and confidence>=.42:
            item.coverage_status="Possible Match"
        else:
            item.coverage_status="Missing"
            task=None
        item.matched_task_code=task.get("task_code") if task else None
        item.matched_task_name=task.get("task_name") if task else None
        item.match_confidence=Decimal(str(confidence)) if confidence else None
        if item.coverage_status=="Covered":
            item.disposition_status="Confirmed Covered"
            item.disposition_reason=None
        elif previous=="Covered" and item.coverage_status!="Covered":
            item.disposition_status="Unexplained"
            item.disposition_reason=None
    db.add(AuditEvent(
        user_id=user_id,bid_project_id=bid_id,event_type="schedule.scope_coverage_evaluated",
        entity_type="BidProject",entity_id=str(bid_id),request_metadata=request_metadata or {},
        details={"expected_items":len(items),"schedule_activities":len(tasks)},
    ))
    db.commit()
    rows=[{**_scope_item_dict(x),"candidate_matches":candidate_matches.get(x.id,[])} for x in items]
    authority_order={"BOQ":0,"Contract / Technical Requirement":1,"Manual":2,"Project-Type Knowledge":3}
    coverage_order={"Missing":0,"Possible Match":1,"Not Checked":2,"Covered":3}
    rows.sort(key=lambda x:(
        0 if x["blocking"] else 1,
        authority_order.get(x["source_type"],2),
        coverage_order.get(x["coverage_status"],4),
        x["activity_level"],
        x["activity_name"].lower(),
    ))
    blocking=[x for x in rows if x["blocking"]]
    return {
        "items":rows,
        "summary":{
            "expected":len(rows),
            "covered":sum(1 for x in rows if x["coverage_status"]=="Covered"),
            "possible_match":sum(1 for x in rows if x["coverage_status"]=="Possible Match"),
            "missing":sum(1 for x in rows if x["coverage_status"]=="Missing"),
            "blocking":len(blocking),
            "knowledge_warnings":sum(1 for x in rows if x["source_type"]=="Project-Type Knowledge" and x["coverage_status"]!="Covered"),
            "contract_items":sum(1 for x in rows if x["source_type"]=="Contract / Technical Requirement"),
            "boq_items":sum(1 for x in rows if x["source_type"]=="BOQ"),
            "project_type_items":sum(1 for x in rows if x["source_type"]=="Project-Type Knowledge"),
            "explained_missing":sum(1 for x in rows if x["coverage_status"]=="Missing" and not x["blocking"]),
        },
        "ready":len(blocking)==0 and len(rows)>0,
        "grade":"Complete" if len(blocking)==0 and rows else "Action Required" if rows else "No Scope Catalog",
        "methodology":"phase6-schedule-scope-coverage-v5",
        "note":"Expected activities are independently sourced from bid scope. Missing or ambiguous coverage must be explained; 'To Be Added' remains a blocker until a revised schedule contains the activity.",
    }


def disposition_scope_item(
    db:Session,item_id:int,status:str,reason:str|None,user_id:int,request_metadata:dict|None=None
):
    allowed={"Unexplained","Confirmed Covered","To Be Added","Covered Elsewhere","Not Applicable","Explained-Excluded"}
    if status not in allowed:raise ValueError("Invalid disposition status")
    item=db.get(ScheduleScopeItem,item_id)
    if not item:raise ValueError("Schedule scope item not found")
    reason=(reason or "").strip() or None
    if status in {"Covered Elsewhere","Not Applicable","Explained-Excluded","To Be Added"} and not reason:
        raise ValueError("A reason is required for this disposition")
    if status=="Confirmed Covered" and item.coverage_status not in {"Covered","Possible Match"}:
        raise ValueError("Only a covered or possible-match item can be confirmed covered")
    item.disposition_status=status
    item.disposition_reason=reason
    item.disposition_by=user_id
    item.disposition_at=datetime.now(timezone.utc)
    db.add(AuditEvent(
        user_id=user_id,bid_project_id=item.bid_project_id,event_type="schedule.scope_item_dispositioned",
        entity_type="ScheduleScopeItem",entity_id=str(item.id),request_metadata=request_metadata or {},
        details={"status":status,"reason":reason},
    ))
    db.commit();db.refresh(item)
    return _scope_item_dict(item)
