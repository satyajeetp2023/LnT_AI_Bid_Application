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


def build_schedule_optimization_advisor(
    content:bytes,
    near_critical_hours:float=40.0,
    long_duration_hours:float=160.0,
):
    tables=parse_xer(content)
    tasks=tables.get("TASK",[])
    rels=tables.get("TASKPRED",[])
    assignments=tables.get("TASKRSRC",[])
    calendars=tables.get("CALENDAR",[])

    preds=defaultdict(list);succs=defaultdict(list)
    for rel in rels:
        if rel.get("task_id"):preds[rel.get("task_id")].append(rel)
        if rel.get("pred_task_id"):succs[rel.get("pred_task_id")].append(rel)

    task_resources=Counter(x.get("task_id") for x in assignments if x.get("task_id"))
    milestone_types={"TT_Mile","TT_FinMile","TT_StartMile","TT_FinishMile"}
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
        score=0

        if task_type not in milestone_types and not preds.get(task_id):
            issues.append("No predecessor / open start")
            opportunities.append("Review whether a predecessor or release condition should be added.")
            score+=22
        if task_type not in milestone_types and not succs.get(task_id):
            issues.append("No successor / open finish")
            opportunities.append("Review whether downstream logic or a completion tie is missing.")
            score+=22

        if total_float<0:
            issues.append("Negative total float")
            opportunities.append("Do not compress automatically. Review logic, constraints, duration and contractual milestone assumptions first.")
            score+=28
        elif total_float<=near_critical_hours:
            issues.append("Near-critical float")
            opportunities.append("Treat as sensitive. Test sequencing, duration and resource assumptions before consuming available float.")
            score+=18
        elif total_float>near_critical_hours:
            opportunities.append("Available float may allow resequencing or resource smoothing, subject to access, procurement and interface constraints.")
            score+=5

        if duration>long_duration_hours and task_type not in milestone_types:
            issues.append("Long duration")
            opportunities.append("Review whether the activity can be broken into measurable work fronts or shorter control activities.")
            score+=16

        lagged=[x for x in preds.get(task_id,[]) if abs(_float(x.get("lag_hr_cnt")))>.001]
        if lagged:
            issues.append(f"{len(lagged)} predecessor relationship(s) with lag")
            opportunities.append("Review whether lag can be replaced by an explicit activity for clearer logic and progress measurement.")
            score+=min(15,5*len(lagged))

        cstr=str(task.get("cstr_type") or "").strip()
        cstr2=str(task.get("cstr_type2") or "").strip()
        if (cstr and cstr not in {"CS_None","None"}) or (cstr2 and cstr2 not in {"CS_None","None"}):
            issues.append("Constraint applied")
            opportunities.append("Check whether the constraint is contractually required or can be represented through logic.")
            score+=14

        resource_count=task_resources.get(task_id,0)
        if assignments and resource_count==0 and task_type not in milestone_types:
            issues.append("No resource assignment")
            opportunities.append("Review whether the activity should be resource-loaded for more realistic sequencing and duration.")
            score+=10
        elif resource_count>0 and total_float>near_critical_hours:
            opportunities.append("Resource-loaded activity with float may be a candidate for resource leveling without affecting key milestones.")
            score+=4

        if len(preds.get(task_id,[]))>4 or len(succs.get(task_id,[]))>4:
            issues.append("High logic density")
            opportunities.append("Review dense logic for redundant ties or unnecessary constraints on sequencing.")
            score+=8

        if score<8 and not issues:continue

        candidates.append({
            **_task_label(task),
            "total_float_hours":total_float,
            "duration_hours":duration,
            "predecessor_count":len(preds.get(task_id,[])),
            "successor_count":len(succs.get(task_id,[])),
            "resource_assignment_count":resource_count,
            "issues":issues,
            "adjustment_opportunities":opportunities,
            "adjustability_score":min(100,score),
            "priority":"High" if score>=45 else "Medium" if score>=25 else "Low",
            "guardrail":"Recommendation only. Recalculate in Primavera after any change and verify milestones, interfaces, resources, calendars and contractual requirements.",
        })

    candidates.sort(key=lambda x:(-x["adjustability_score"],x["total_float_hours"],x.get("task_code") or ""))

    table_inventory=_table_inventory(tables)
    return {
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
            "high_priority":sum(1 for x in candidates if x["priority"]=="High"),
            "medium_priority":sum(1 for x in candidates if x["priority"]=="Medium"),
            "low_priority":sum(1 for x in candidates if x["priority"]=="Low"),
            "candidates":candidates,
            "methodology":"phase6-schedule-optimization-advisor-v1",
            "note":"The advisor identifies activities worth reviewing for schedule refinement. It never changes the schedule automatically.",
        },
    }
