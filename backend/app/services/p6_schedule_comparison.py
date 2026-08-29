from datetime import datetime

from app.services.p6_xer import parse_xer


DATE_FORMATS=(
    "%Y-%m-%d %H:%M","%Y-%m-%d %H:%M:%S","%Y-%m-%d",
    "%d-%b-%y %H:%M","%d-%b-%Y %H:%M","%d-%b-%y","%d-%b-%Y",
)


def _date(value):
    text=str(value or "").strip()
    if not text:return None
    for fmt in DATE_FORMATS:
        try:return datetime.strptime(text,fmt)
        except ValueError:pass
    return None


def _float(value):
    try:return float(value)
    except (TypeError,ValueError):return 0.0


def _key(task):
    return task.get("task_code") or task.get("task_id")


def _forecast_start(task):
    return _date(task.get("act_start_date")) or _date(task.get("early_start_date")) or _date(task.get("target_start_date")) or _date(task.get("late_start_date"))


def _forecast_finish(task):
    return _date(task.get("act_end_date")) or _date(task.get("early_end_date")) or _date(task.get("target_end_date")) or _date(task.get("late_end_date"))


def _days(current,baseline):
    if not current or not baseline:return None
    return round((current-baseline).total_seconds()/86400,2)


def _task_row(base,current):
    base_start=_forecast_start(base)
    cur_start=_forecast_start(current)
    base_finish=_forecast_finish(base)
    cur_finish=_forecast_finish(current)
    return {
        "task_code":current.get("task_code") or base.get("task_code"),
        "task_name":current.get("task_name") or base.get("task_name"),
        "wbs_id":current.get("wbs_id") or base.get("wbs_id"),
        "baseline_status":base.get("status_code"),
        "current_status":current.get("status_code"),
        "baseline_start":base_start.isoformat() if base_start else None,
        "current_start":cur_start.isoformat() if cur_start else None,
        "start_variance_days":_days(cur_start,base_start),
        "baseline_finish":base_finish.isoformat() if base_finish else None,
        "current_finish":cur_finish.isoformat() if cur_finish else None,
        "finish_variance_days":_days(cur_finish,base_finish),
        "baseline_duration_hours":max(_float(base.get("target_drtn_hr_cnt")),_float(base.get("remain_drtn_hr_cnt"))),
        "current_duration_hours":max(_float(current.get("target_drtn_hr_cnt")),_float(current.get("remain_drtn_hr_cnt"))),
        "duration_change_hours":round(max(_float(current.get("target_drtn_hr_cnt")),_float(current.get("remain_drtn_hr_cnt")))-max(_float(base.get("target_drtn_hr_cnt")),_float(base.get("remain_drtn_hr_cnt"))),2),
        "baseline_total_float_hours":_float(base.get("total_float_hr_cnt")),
        "current_total_float_hours":_float(current.get("total_float_hr_cnt")),
        "float_change_hours":round(_float(current.get("total_float_hr_cnt"))-_float(base.get("total_float_hr_cnt")),2),
        "status_changed":base.get("status_code")!=current.get("status_code"),
        "task_type":current.get("task_type") or base.get("task_type"),
    }


def _relation_key(rel,task_map):
    task=task_map.get(rel.get("task_id"))
    pred=task_map.get(rel.get("pred_task_id"))
    return (
        _key(pred or {"task_id":rel.get("pred_task_id")}),
        _key(task or {"task_id":rel.get("task_id")}),
        rel.get("pred_type") or "",
        round(_float(rel.get("lag_hr_cnt")),3),
    )


def compare_xer(baseline_content:bytes,current_content:bytes)->dict:
    base=parse_xer(baseline_content)
    cur=parse_xer(current_content)
    base_tasks=base.get("TASK",[])
    cur_tasks=cur.get("TASK",[])
    base_by_key={_key(x):x for x in base_tasks if _key(x)}
    cur_by_key={_key(x):x for x in cur_tasks if _key(x)}

    common=sorted(set(base_by_key)&set(cur_by_key))
    added=[cur_by_key[k] for k in sorted(set(cur_by_key)-set(base_by_key))]
    deleted=[base_by_key[k] for k in sorted(set(base_by_key)-set(cur_by_key))]
    changes=[_task_row(base_by_key[k],cur_by_key[k]) for k in common]

    finish_slippage=[x for x in changes if x["finish_variance_days"] is not None and x["finish_variance_days"]>0]
    start_slippage=[x for x in changes if x["start_variance_days"] is not None and x["start_variance_days"]>0]
    duration_changes=[x for x in changes if abs(x["duration_change_hours"])>.01]
    float_changes=[x for x in changes if abs(x["float_change_hours"])>.01]
    status_changes=[x for x in changes if x["status_changed"]]

    milestone_types={"TT_Mile","TT_FinMile","TT_StartMile","TT_FinishMile"}
    milestone_changes=[x for x in changes if x.get("task_type") in milestone_types and x["finish_variance_days"] is not None and abs(x["finish_variance_days"])>.01]

    base_task_id_map={x.get("task_id"):x for x in base_tasks}
    cur_task_id_map={x.get("task_id"):x for x in cur_tasks}
    base_rel={_relation_key(x,base_task_id_map) for x in base.get("TASKPRED",[])}
    cur_rel={_relation_key(x,cur_task_id_map) for x in cur.get("TASKPRED",[])}
    added_rel=sorted(cur_rel-base_rel)
    deleted_rel=sorted(base_rel-cur_rel)

    base_project=(base.get("PROJECT") or [{}])[0]
    cur_project=(cur.get("PROJECT") or [{}])[0]
    base_dd=_date(base_project.get("last_recalc_date") or base_project.get("last_schedule_date") or base_project.get("data_date"))
    cur_dd=_date(cur_project.get("last_recalc_date") or cur_project.get("last_schedule_date") or cur_project.get("data_date"))

    finish_slippage.sort(key=lambda x:x["finish_variance_days"],reverse=True)
    start_slippage.sort(key=lambda x:x["start_variance_days"],reverse=True)
    milestone_changes.sort(key=lambda x:abs(x["finish_variance_days"]),reverse=True)

    return {
        "baseline":{
            "project_code":base_project.get("proj_short_name"),
            "project_name":base_project.get("proj_name"),
            "data_date":base_dd.isoformat() if base_dd else None,
            "activities":len(base_tasks),
            "relationships":len(base.get("TASKPRED",[])),
        },
        "current":{
            "project_code":cur_project.get("proj_short_name"),
            "project_name":cur_project.get("proj_name"),
            "data_date":cur_dd.isoformat() if cur_dd else None,
            "activities":len(cur_tasks),
            "relationships":len(cur.get("TASKPRED",[])),
        },
        "summary":{
            "common_activities":len(common),
            "added_activities":len(added),
            "deleted_activities":len(deleted),
            "finish_slippages":len(finish_slippage),
            "start_slippages":len(start_slippage),
            "duration_changes":len(duration_changes),
            "float_changes":len(float_changes),
            "status_changes":len(status_changes),
            "milestone_changes":len(milestone_changes),
            "added_relationships":len(added_rel),
            "deleted_relationships":len(deleted_rel),
            "data_date_shift_days":_days(cur_dd,base_dd),
        },
        "added_activities":[{
            "task_code":x.get("task_code"),"task_name":x.get("task_name"),"task_type":x.get("task_type"),"wbs_id":x.get("wbs_id")
        } for x in added],
        "deleted_activities":[{
            "task_code":x.get("task_code"),"task_name":x.get("task_name"),"task_type":x.get("task_type"),"wbs_id":x.get("wbs_id")
        } for x in deleted],
        "finish_slippage":finish_slippage,
        "start_slippage":start_slippage,
        "duration_changes":duration_changes,
        "float_changes":float_changes,
        "status_changes":status_changes,
        "milestone_changes":milestone_changes,
        "added_relationships":[{
            "predecessor":x[0],"successor":x[1],"type":x[2],"lag_hours":x[3]
        } for x in added_rel],
        "deleted_relationships":[{
            "predecessor":x[0],"successor":x[1],"type":x[2],"lag_hours":x[3]
        } for x in deleted_rel],
        "comparison_version":"phase6-xer-comparison-v1",
        "note":"This is a deterministic schedule-version comparison. It does not by itself establish contractual delay responsibility or entitlement.",
    }
