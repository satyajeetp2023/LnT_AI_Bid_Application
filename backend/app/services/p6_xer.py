from collections import Counter,defaultdict
from datetime import datetime
from math import isfinite


DATE_FORMATS=(
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d-%b-%y %H:%M",
    "%d-%b-%Y %H:%M",
    "%d-%b-%y",
    "%d-%b-%Y",
)


def _decode(content:bytes)->str:
    for encoding in ("utf-8-sig","cp1252","latin-1"):
        try:return content.decode(encoding)
        except UnicodeDecodeError:continue
    return content.decode("utf-8",errors="replace")


def parse_xer(content:bytes)->dict[str,list[dict]]:
    text=_decode(content)
    tables={}
    table_name=None
    fields=[]
    rows=[]
    for raw in text.splitlines():
        if not raw:continue
        parts=raw.rstrip("\r\n").split("\t")
        marker=parts[0]
        if marker=="%T":
            if table_name is not None:tables[table_name]=rows
            table_name=parts[1].strip() if len(parts)>1 else ""
            fields=[];rows=[]
        elif marker=="%F" and table_name:
            fields=[x.strip() for x in parts[1:]]
        elif marker=="%R" and table_name and fields:
            values=parts[1:]
            if len(values)<len(fields):values+=[""]*(len(fields)-len(values))
            rows.append(dict(zip(fields,values[:len(fields)])))
        elif marker=="%E":
            if table_name is not None:tables[table_name]=rows
            table_name=None;fields=[];rows=[]
    if table_name is not None:tables[table_name]=rows
    return tables


def _float(value,default=0.0):
    try:
        result=float(value)
        return result if isfinite(result) else default
    except (TypeError,ValueError):return default


def _date(value):
    text=str(value or "").strip()
    if not text:return None
    for fmt in DATE_FORMATS:
        try:return datetime.strptime(text,fmt)
        except ValueError:pass
    return None


def _iso(value):
    parsed=_date(value)
    return parsed.isoformat() if parsed else (str(value).strip() or None)


def _task_label(task):
    return {
        "task_id":task.get("task_id"),
        "task_code":task.get("task_code"),
        "task_name":task.get("task_name"),
        "status_code":task.get("status_code"),
        "task_type":task.get("task_type"),
        "wbs_id":task.get("wbs_id"),
    }


def analyze_schedule_tables(tables:dict[str,list[dict]],long_duration_hours:float=160.0,near_critical_hours:float=40.0,capabilities:dict|None=None)->dict:
    projects=tables.get("PROJECT",[])
    tasks=tables.get("TASK",[])
    rels=tables.get("TASKPRED",[])
    wbs=tables.get("PROJWBS",[])
    calendars=tables.get("CALENDAR",[])
    resources=tables.get("RSRC",[])
    assignments=tables.get("TASKRSRC",[])
    capabilities=capabilities or {}
    logic_available=bool(capabilities.get("logic",bool(rels)))
    float_available=bool(capabilities.get("float",any(str(x.get("total_float_hr_cnt") or "").strip() for x in tasks)))

    task_by_id={x.get("task_id"):x for x in tasks if x.get("task_id")}
    preds=defaultdict(list);succs=defaultdict(list)
    dangling=[]
    lagged=[]
    for rel in rels:
        task_id=rel.get("task_id");pred_id=rel.get("pred_task_id")
        if task_id:preds[task_id].append(rel)
        if pred_id:succs[pred_id].append(rel)
        if task_id not in task_by_id or pred_id not in task_by_id:
            dangling.append({
                "task_id":task_id,"pred_task_id":pred_id,
                "pred_type":rel.get("pred_type"),"lag_hours":_float(rel.get("lag_hr_cnt")),
            })
        lag=_float(rel.get("lag_hr_cnt"))
        if abs(lag)>.001:
            lagged.append({
                "task_id":task_id,"pred_task_id":pred_id,
                "pred_type":rel.get("pred_type"),"lag_hours":lag,
            })

    milestones={"TT_Mile","TT_FinMile","TT_StartMile","TT_FinishMile"}
    complete_statuses={"TK_Complete","Complete","Completed"}
    active_tasks=[x for x in tasks if x.get("status_code") not in complete_statuses]
    non_milestone_active=[x for x in active_tasks if x.get("task_type") not in milestones]

    no_predecessor=[_task_label(x) for x in non_milestone_active if not preds.get(x.get("task_id"))] if logic_available else []
    no_successor=[_task_label(x) for x in non_milestone_active if not succs.get(x.get("task_id"))] if logic_available else []

    negative_float=[]
    zero_or_negative_float=[]
    critical_float=[]
    near_critical_float=[]
    long_duration=[]
    constrained=[]
    status_date_issues=[]
    missing_wbs=[]
    for task in tasks:
        total_float=_float(task.get("total_float_hr_cnt")) if float_available else None
        if float_available and total_float is not None and total_float<0:
            negative_float.append({**_task_label(task),"total_float_hours":total_float})
        if float_available and total_float is not None and total_float<=0:
            zero_or_negative_float.append({**_task_label(task),"total_float_hours":total_float})
            if task.get("status_code") not in complete_statuses:
                critical_float.append({**_task_label(task),"total_float_hours":total_float})
        elif float_available and total_float is not None and total_float<=near_critical_hours and task.get("status_code") not in complete_statuses:
            near_critical_float.append({**_task_label(task),"total_float_hours":total_float})

        duration=max(_float(task.get("target_drtn_hr_cnt")),_float(task.get("remain_drtn_hr_cnt")))
        if duration>long_duration_hours and task.get("task_type") not in milestones:
            long_duration.append({**_task_label(task),"duration_hours":duration})

        cstr=str(task.get("cstr_type") or "").strip()
        cstr2=str(task.get("cstr_type2") or "").strip()
        if (cstr and cstr not in {"CS_None","None"}) or (cstr2 and cstr2 not in {"CS_None","None"}):
            constrained.append({**_task_label(task),"constraint_type":cstr or None,"constraint_type_2":cstr2 or None,"constraint_date":_iso(task.get("cstr_date")),"constraint_date_2":_iso(task.get("cstr_date2"))})

        status=str(task.get("status_code") or "")
        actual_start=_date(task.get("act_start_date"))
        actual_finish=_date(task.get("act_end_date"))
        if status in {"TK_NotStart","Not Started"} and (actual_start or actual_finish):
            status_date_issues.append({**_task_label(task),"issue":"Not-started activity contains actual dates."})
        elif status in {"TK_Active","In Progress"} and not actual_start:
            status_date_issues.append({**_task_label(task),"issue":"In-progress activity has no actual start."})
        elif status in complete_statuses and not actual_finish:
            status_date_issues.append({**_task_label(task),"issue":"Completed activity has no actual finish."})

        if not task.get("wbs_id"):
            missing_wbs.append(_task_label(task))

    relation_types=Counter(x.get("pred_type") or "Unknown" for x in rels)
    activity_statuses=Counter(x.get("status_code") or "Unknown" for x in tasks)
    activity_types=Counter(x.get("task_type") or "Unknown" for x in tasks)

    milestone_rows=[]
    for task in tasks:
        if task.get("task_type") not in milestones:continue
        finish=task.get("act_end_date") or task.get("early_end_date") or task.get("target_end_date") or task.get("late_end_date")
        tf=_float(task.get("total_float_hr_cnt"))
        milestone_rows.append({
            **_task_label(task),
            "finish_date":_iso(finish),
            "total_float_hours":tf,
            "criticality":"Critical" if tf<=0 else "Near Critical" if tf<=near_critical_hours else "Normal",
        })

    project=projects[0] if projects else {}
    data_date=project.get("last_recalc_date") or project.get("last_schedule_date") or project.get("data_date")
    planned_start=_date(project.get("plan_start_date"))
    planned_finish=_date(project.get("plan_end_date") or project.get("scd_end_date"))
    planned_duration_days=(planned_finish-planned_start).total_seconds()/86400 if planned_start and planned_finish else None
    issue_counts={
        "open_start":len(no_predecessor),
        "open_finish":len(no_successor),
        "negative_float":len(negative_float),
        "constraints":len(constrained),
        "long_duration":len(long_duration),
        "lagged_relationships":len(lagged),
        "dangling_relationships":len(dangling),
        "status_date_issues":len(status_date_issues),
        "missing_wbs":len(missing_wbs),
        "critical_float":len(critical_float),
        "near_critical_float":len(near_critical_float),
        "milestones_at_risk":sum(1 for x in milestone_rows if x["criticality"] in {"Critical","Near Critical"}),
    }
    denominator=max(1,len(tasks))
    weighted=(
        min(25,issue_counts["open_start"]*100/denominator*.50)+
        min(25,issue_counts["open_finish"]*100/denominator*.50)+
        min(20,issue_counts["negative_float"]*100/denominator*.40)+
        min(10,issue_counts["dangling_relationships"]*2)+
        min(10,issue_counts["status_date_issues"]*100/denominator*.30)+
        min(10,issue_counts["constraints"]*100/denominator*.15)
    )
    health_score=round(max(0.0,100-weighted),1)

    return {
        "project":{
            "project_id":project.get("proj_id"),
            "project_code":project.get("proj_short_name"),
            "project_name":project.get("proj_name"),
            "data_date":_iso(data_date),
            "planned_start":_iso(project.get("plan_start_date")),
            "planned_finish":_iso(project.get("plan_end_date") or project.get("scd_end_date")),
            "planned_duration_days":round(planned_duration_days,1) if planned_duration_days is not None else None,
        },
        "counts":{
            "projects":len(projects),
            "activities":len(tasks),
            "active_activities":len(active_tasks),
            "relationships":len(rels),
            "wbs_nodes":len(wbs),
            "calendars":len(calendars),
            "resources":len(resources),
            "resource_assignments":len(assignments),
        },
        "criticality":{
            "method":"Total Float screening" if float_available else "Not available from source",
            "critical_threshold_hours":0.0,
            "near_critical_threshold_hours":near_critical_hours,
            "critical_activities":critical_float,
            "near_critical_activities":near_critical_float,
            "milestones_at_risk":[x for x in milestone_rows if x["criticality"] in {"Critical","Near Critical"}],
            "note":"This is a float-based screening view. It does not independently recalculate Primavera's CPM path." if float_available else "Total float is not available from this source, so criticality is not inferred.",
        },
        "health":{
            "score":health_score,
            "grade":"Good" if health_score>=85 else "Needs Attention" if health_score>=65 else "Poor",
            "issue_counts":issue_counts,
            "methodology":"phase6-schedule-health-v2",
            "note":"The score uses only parameters available from the uploaded source. Unavailable logic or float data is not treated as a defect.",
        },
        "milestones":milestone_rows,
        "distributions":{
            "activity_statuses":[{"name":k,"count":v} for k,v in activity_statuses.most_common()],
            "activity_types":[{"name":k,"count":v} for k,v in activity_types.most_common()],
            "relationship_types":[{"name":k,"count":v} for k,v in relation_types.most_common()],
        },
        "issues":{
            "open_start":no_predecessor,
            "open_finish":no_successor,
            "negative_float":negative_float,
            "zero_or_negative_float":zero_or_negative_float,
            "critical_float":critical_float,
            "near_critical_float":near_critical_float,
            "constraints":constrained,
            "long_duration":long_duration,
            "lagged_relationships":lagged,
            "dangling_relationships":dangling,
            "status_date_issues":status_date_issues,
            "missing_wbs":missing_wbs,
        },
        "source_tables":sorted(tables),
        "parser_version":"phase6-schedule-table-analyzer-v1",
    }


def analyze_xer(content:bytes,long_duration_hours:float=160.0,near_critical_hours:float=40.0)->dict:
    result=analyze_schedule_tables(parse_xer(content),long_duration_hours,near_critical_hours)
    result["parser_version"]="phase6-xer-parser-v4"
    return result
