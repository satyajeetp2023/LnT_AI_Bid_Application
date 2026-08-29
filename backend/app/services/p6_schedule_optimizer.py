from collections import Counter,defaultdict

from app.services.p6_xer import parse_xer


def _float(value,default=0.0):
    try:return float(value)
    except (TypeError,ValueError):return default


def _task_label(task):
    return {
        "task_id":task.get("task_id"),
        "task_code":task.get("task_code"),
        "task_name":task.get("task_name"),
        "status_code":task.get("status_code"),
        "task_type":task.get("task_type"),
        "wbs_id":task.get("wbs_id"),
    }


def _table_inventory(tables:dict[str,list[dict]]):
    result=[]
    for name,rows in sorted(tables.items()):
        fields=sorted({key for row in rows for key in row})
        populated={field:sum(1 for row in rows if str(row.get(field) or "").strip()) for field in fields}
        result.append({
            "table":name,
            "rows":len(rows),
            "fields":fields,
            "field_count":len(fields),
            "populated_counts":populated,
        })
    return result


def activity_parameter_profile(content:bytes,task_key:str):
    tables=parse_xer(content)
    tasks=tables.get("TASK",[])
    task=next((x for x in tasks if str(x.get("task_code") or "")==str(task_key) or str(x.get("task_id") or "")==str(task_key)),None)
    if not task:return None
    task_id=task.get("task_id")
    rels=tables.get("TASKPRED",[])
    predecessors=[x for x in rels if x.get("task_id")==task_id]
    successors=[x for x in rels if x.get("pred_task_id")==task_id]
    assignments=[x for x in tables.get("TASKRSRC",[]) if x.get("task_id")==task_id]
    task_codes=[x for x in tables.get("TASKACTV",[]) if x.get("task_id")==task_id]
    calendar_id=task.get("clndr_id")
    calendar=next((x for x in tables.get("CALENDAR",[]) if x.get("clndr_id")==calendar_id),None)
    wbs_id=task.get("wbs_id")
    wbs=next((x for x in tables.get("PROJWBS",[]) if x.get("wbs_id")==wbs_id),None)
    resources={x.get("rsrc_id"):x for x in tables.get("RSRC",[]) if x.get("rsrc_id")}
    return {
        "task_key":task_key,
        "task":task,
        "wbs":wbs,
        "calendar":calendar,
        "predecessors":predecessors,
        "successors":successors,
        "resource_assignments":[{**x,"resource":resources.get(x.get("rsrc_id"))} for x in assignments],
        "activity_codes":task_codes,
        "field_summary":{
            "task_fields":len(task),
            "populated_task_fields":sum(1 for v in task.values() if str(v or "").strip()),
            "predecessor_count":len(predecessors),
            "successor_count":len(successors),
            "resource_assignment_count":len(assignments),
            "activity_code_count":len(task_codes),
        },
        "profile_version":"phase6-activity-parameter-profile-v1",
    }


def build_schedule_optimization_from_tables(
    tables:dict[str,list[dict]],
    near_critical_hours:float=40.0,
    long_duration_hours:float=160.0,
):
    tasks=tables.get("TASK",[])
    rels=tables.get("TASKPRED",[])
    assignments=tables.get("TASKRSRC",[])
    calendars=tables.get("CALENDAR",[])

    preds=defaultdict(list);succs=defaultdict(list)
    for rel in rels:
        if rel.get("task_id"):preds[rel.get("task_id")].append(rel)
        if rel.get("pred_task_id"):succs[rel.get("pred_task_id")].append(rel)

    milestone_types={"TT_Mile","TT_FinMile","TT_StartMile","TT_FinishMile"}
    task_resources=Counter(x.get("task_id") for x in assignments if x.get("task_id"))
    active_task_ids={x.get("task_id") for x in tasks if x.get("task_id") and x.get("task_type") not in milestone_types}
    assigned_task_ids={x.get("task_id") for x in assignments if x.get("task_id")}
    covered_active=len(active_task_ids&assigned_task_ids)
    coverage_ratio=covered_active/max(1,len(active_task_ids))
    resource_types=Counter()
    resource_map={x.get("rsrc_id"):x for x in tables.get("RSRC",[]) if x.get("rsrc_id")}
    for assignment in assignments:
        resource=resource_map.get(assignment.get("rsrc_id")) or {}
        rtype=resource.get("rsrc_type") or resource.get("resource_type") or "Unspecified"
        resource_types[str(rtype)]+=1
    if not assignments:
        loading_status="Not Resource Loaded"
    elif coverage_ratio>=.90:
        loading_status="Broadly Resource Loaded"
    else:
        loading_status="Partially Resource Loaded"

    active_non_milestone=[x for x in tasks if x.get("task_type") not in milestone_types]
    completeness_checks=[]
    def add_check(name,predicate,required=True):
        denominator=len(active_non_milestone)
        populated=sum(1 for task in active_non_milestone if predicate(task))
        completeness_checks.append({
            "parameter":name,
            "required":required,
            "populated":populated,
            "total":denominator,
            "percent":100.0 if denominator==0 else round(populated*100/denominator,1),
            "missing_activity_codes":[
                task.get("task_code") or task.get("task_id")
                for task in active_non_milestone if not predicate(task)
            ][:100],
        })
    add_check("Activity ID / Code",lambda t:bool(str(t.get("task_code") or "").strip()))
    add_check("Activity Name",lambda t:bool(str(t.get("task_name") or "").strip()))
    add_check("WBS Assignment",lambda t:bool(str(t.get("wbs_id") or "").strip()))
    add_check("Calendar",lambda t:bool(str(t.get("clndr_id") or "").strip()))
    add_check("Status",lambda t:bool(str(t.get("status_code") or "").strip()))
    add_check("Duration",lambda t:_float(t.get("target_drtn_hr_cnt"))>0 or _float(t.get("remain_drtn_hr_cnt"))>0)
    add_check("Start Date",lambda t:any(str(t.get(k) or "").strip() for k in ("act_start_date","early_start_date","target_start_date","late_start_date")))
    add_check("Finish Date",lambda t:any(str(t.get(k) or "").strip() for k in ("act_end_date","early_end_date","target_end_date","late_end_date")))
    add_check("Total Float",lambda t:str(t.get("total_float_hr_cnt") or "").strip()!="")
    add_check("Logic",lambda t:bool(preds.get(t.get("task_id")) or succs.get(t.get("task_id"))))
    if assignments:
        add_check("Resource Assignment",lambda t:t.get("task_id") in assigned_task_ids,required=False)
    required_checks=[x for x in completeness_checks if x["required"]]
    data_completeness_score=100.0 if not required_checks else round(sum(x["percent"] for x in required_checks)/len(required_checks),1)

    complete_statuses={"TK_Complete","Complete","Completed"}

    candidates=[]
    for task in tasks:
        if task.get("status_code") in complete_statuses:continue
        task_id=task.get("task_id")
        total_float=_float(task.get("total_float_hr_cnt"))
        duration=max(_float(task.get("target_drtn_hr_cnt")),_float(task.get("remain_drtn_hr_cnt")))
        task_type=task.get("task_type")
        issues=[]
        opportunities=[]
        review_score=0
        adjustment_score=0
        adjustment_types=[]

        if task_type not in milestone_types and not preds.get(task_id):
            issues.append("No predecessor / open start")
            opportunities.append("Review whether a predecessor or release condition should be added.")
            review_score+=22
        if task_type not in milestone_types and not succs.get(task_id):
            issues.append("No successor / open finish")
            opportunities.append("Review whether downstream logic or a completion tie is missing.")
            review_score+=22

        if total_float<0:
            issues.append("Negative total float")
            opportunities.append("Do not compress automatically. Review logic, constraints, duration and contractual milestone assumptions first.")
            review_score+=28
        elif total_float<=near_critical_hours:
            issues.append("Near-critical float")
            opportunities.append("Treat as sensitive. Test sequencing, duration and resource assumptions before consuming available float.")
            review_score+=18
        elif total_float>near_critical_hours:
            opportunities.append("Available float may allow resequencing or resource smoothing, subject to access, procurement and interface constraints.")
            adjustment_score+=20
            adjustment_types.extend(["Resequencing","Resource smoothing"])

        if duration>long_duration_hours and task_type not in milestone_types:
            issues.append("Long duration")
            opportunities.append("Review whether the activity can be broken into measurable work fronts or shorter control activities.")
            review_score+=16
            adjustment_score+=16
            adjustment_types.append("Duration / work-front breakdown")

        lagged=[x for x in preds.get(task_id,[]) if abs(_float(x.get("lag_hr_cnt")))>.001]
        if lagged:
            issues.append(f"{len(lagged)} predecessor relationship(s) with lag")
            opportunities.append("Review whether lag can be replaced by an explicit activity for clearer logic and progress measurement.")
            review_score+=min(15,5*len(lagged))
            adjustment_score+=min(12,4*len(lagged))
            adjustment_types.append("Logic / lag refinement")

        cstr=str(task.get("cstr_type") or "").strip()
        cstr2=str(task.get("cstr_type2") or "").strip()
        if (cstr and cstr not in {"CS_None","None"}) or (cstr2 and cstr2 not in {"CS_None","None"}):
            issues.append("Constraint applied")
            opportunities.append("Check whether the constraint is contractually required or can be represented through logic.")
            review_score+=14
            adjustment_types.append("Constraint review")

        resource_count=task_resources.get(task_id,0)
        if assignments and resource_count==0 and task_type not in milestone_types:
            issues.append("No resource assignment")
            opportunities.append("Review whether the activity should be resource-loaded for more realistic sequencing and duration.")
            review_score+=10
            adjustment_types.append("Resource loading review")
        elif resource_count>0 and total_float>near_critical_hours:
            opportunities.append("Resource-loaded activity with float may be a candidate for resource leveling without affecting key milestones.")
            adjustment_score+=10
            adjustment_types.append("Resource leveling")

        if len(preds.get(task_id,[]))>4 or len(succs.get(task_id,[]))>4:
            issues.append("High logic density")
            opportunities.append("Review dense logic for redundant ties or unnecessary constraints on sequencing.")
            review_score+=8
            adjustment_score+=6
            adjustment_types.append("Logic simplification")

        hard_constraint=((cstr and cstr not in {"CS_None","None"}) or (cstr2 and cstr2 not in {"CS_None","None"}))
        if total_float<=0:
            adjustment_score=max(0,adjustment_score-20)
        elif total_float<=near_critical_hours:
            adjustment_score=max(0,adjustment_score-10)
        if hard_constraint:
            adjustment_score=max(0,adjustment_score-8)
        if task_type in milestone_types:
            adjustment_score=0
        if review_score<8 and adjustment_score<8 and not issues:continue

        candidates.append({
            **_task_label(task),
            "total_float_hours":total_float,
            "duration_hours":duration,
            "predecessor_count":len(preds.get(task_id,[])),
            "successor_count":len(succs.get(task_id,[])),
            "resource_assignment_count":resource_count,
            "issues":issues,
            "adjustment_opportunities":opportunities,
            "review_priority_score":min(100,review_score),
            "adjustability_score":min(100,adjustment_score),
            "review_priority":"High" if review_score>=45 else "Medium" if review_score>=25 else "Low",
            "adjustment_potential":"High" if adjustment_score>=35 else "Medium" if adjustment_score>=18 else "Low",
            "adjustment_types":sorted(set(adjustment_types)),
            "guardrail":"Recommendation only. Recalculate in Primavera after any change and verify milestones, interfaces, resources, calendars and contractual requirements.",
        })

    candidates.sort(key=lambda x:(-x["review_priority_score"],-x["adjustability_score"],x["total_float_hours"],x.get("task_code") or ""))

    table_inventory=_table_inventory(tables)
    return {
        "data_completeness":{
            "score":data_completeness_score,
            "grade":"Complete" if data_completeness_score>=95 else "Needs Attention" if data_completeness_score>=80 else "Incomplete",
            "checks":completeness_checks,
            "note":"Resource completeness is shown only when the schedule actually contains resource assignments. Contract-specific resource requirements are checked separately.",
        },
        "resource_loading":{
            "status":loading_status,
            "activities_with_assignments":covered_active,
            "eligible_activities":len(active_task_ids),
            "coverage_ratio":round(coverage_ratio,3),
            "assignment_count":len(assignments),
            "resource_types":[{"name":k,"count":v} for k,v in resource_types.most_common()],
            "note":"Resource loading is optional. Resource-based recommendations are applied only where assignments exist.",
        },
        "parameter_inventory":{
            "tables":table_inventory,
            "table_count":len(table_inventory),
            "total_fields":sum(x["field_count"] for x in table_inventory),
            "total_rows":sum(x["rows"] for x in table_inventory),
            "calendar_count":len(calendars),
            "note":"All XER tables and fields are inventoried even when the current optimization rules do not yet interpret every field semantically.",
        },
        "optimization":{
            "candidate_count":len(candidates),
            "high_priority":sum(1 for x in candidates if x["review_priority"]=="High"),
            "medium_priority":sum(1 for x in candidates if x["review_priority"]=="Medium"),
            "low_priority":sum(1 for x in candidates if x["review_priority"]=="Low"),
            "high_adjustment_potential":sum(1 for x in candidates if x["adjustment_potential"]=="High"),
            "medium_adjustment_potential":sum(1 for x in candidates if x["adjustment_potential"]=="Medium"),
            "candidates":candidates,
            "methodology":"phase6-schedule-optimization-advisor-v4",
            "note":"The advisor identifies activities worth reviewing for schedule refinement. It never changes the schedule automatically.",
        },
    }


def build_schedule_optimization_advisor(
    content:bytes,
    near_critical_hours:float=40.0,
    long_duration_hours:float=160.0,
):
    return build_schedule_optimization_from_tables(parse_xer(content),near_critical_hours,long_duration_hours)
