from app.services.p6_schedule_comparison import compare_schedule_tables,compare_xer

BASE="""ERMHDR\t8.4\t2026-01-01
%T\tPROJECT
%F\tproj_id\tproj_short_name\tproj_name\tlast_recalc_date
%R\t1\tTEST\tRailway\t2026-01-01 08:00
%T\tTASK
%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\tstatus_code\ttask_type\ttarget_drtn_hr_cnt\tremain_drtn_hr_cnt\ttotal_float_hr_cnt\ttarget_start_date\ttarget_end_date
%R\t10\t1\t1\tA100\tFoundation\tTK_NotStart\tTT_Task\t80\t80\t40\t2026-01-01 08:00\t2026-01-10 17:00
%R\t20\t1\t1\tM100\tSection Complete\tTK_NotStart\tTT_FinMile\t0\t0\t0\t2026-01-10 17:00\t2026-01-10 17:00
%T\tTASKPRED
%F\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt
%R\t20\t10\tPR_FS\t0
%E
"""

CURRENT="""ERMHDR\t8.4\t2026-01-15
%T\tPROJECT
%F\tproj_id\tproj_short_name\tproj_name\tlast_recalc_date
%R\t1\tTEST\tRailway\t2026-01-15 08:00
%T\tTASK
%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\tstatus_code\ttask_type\ttarget_drtn_hr_cnt\tremain_drtn_hr_cnt\ttotal_float_hr_cnt\ttarget_start_date\ttarget_end_date
%R\t10\t1\t1\tA100\tFoundation\tTK_Active\tTT_Task\t120\t80\t8\t2026-01-03 08:00\t2026-01-15 17:00
%R\t20\t1\t1\tM100\tSection Complete\tTK_NotStart\tTT_FinMile\t0\t0\t-8\t2026-01-15 17:00\t2026-01-15 17:00
%R\t30\t1\t1\tA300\tAdditional Work\tTK_NotStart\tTT_Task\t40\t40\t24\t2026-01-11 08:00\t2026-01-15 17:00
%T\tTASKPRED
%F\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt
%R\t30\t10\tPR_FS\t0
%R\t20\t30\tPR_FS\t0
%E
"""

def test_xer_comparison_tracks_slippage_changes_and_relationships():
    result=compare_xer(BASE.encode(),CURRENT.encode())
    assert result["summary"]["added_activities"]==1
    assert result["summary"]["deleted_activities"]==0
    assert result["summary"]["finish_slippages"]==2
    assert result["summary"]["milestone_changes"]==1
    assert result["summary"]["duration_changes"]==1
    assert result["summary"]["float_changes"]==2
    assert result["summary"]["status_changes"]==1
    assert result["summary"]["data_date_shift_days"]==14
    assert result["summary"]["added_relationships"]==2
    assert result["summary"]["deleted_relationships"]==1
    assert result["summary"]["newly_negative_float"]==1
    assert result["summary"]["delayed_milestones"]==1
    assert result["risk_summary"]["risk_level"]=="High"
    assert result["finish_slippage"][0]["finish_variance_days"]>=5


def test_cross_format_comparison_does_not_invent_float_or_logic_changes():
    base={
        "PROJECT":[],
        "TASK":[
            {"task_id":"A100","task_code":"A100","task_name":"Foundation","target_start_date":"2026-01-01","target_end_date":"2026-01-10","target_drtn_hr_cnt":80,"total_float_hr_cnt":24},
            {"task_id":"A200","task_code":"A200","task_name":"Mast Erection","target_start_date":"2026-01-11","target_end_date":"2026-01-20","target_drtn_hr_cnt":80,"total_float_hr_cnt":8},
        ],
        "TASKPRED":[{"task_id":"A200","pred_task_id":"A100","pred_type":"PR_FS","lag_hr_cnt":0}],
    }
    current={
        "PROJECT":[],
        "TASK":[
            {"task_id":"A100","task_code":"A100","task_name":"Foundation","target_start_date":"2026-01-02","target_end_date":"2026-01-12","target_drtn_hr_cnt":80},
            {"task_id":"A200","task_code":"A200","task_name":"Mast Erection","target_start_date":"2026-01-13","target_end_date":"2026-01-22","target_drtn_hr_cnt":80},
        ],
        "TASKPRED":[],
    }
    result=compare_schedule_tables(
        base,current,
        {"float":True,"logic":True},
        {"float":False,"logic":False},
    )
    assert result["summary"]["finish_slippages"]==2
    assert result["summary"]["float_changes"]==0
    assert result["summary"]["newly_negative_float"]==0
    assert result["summary"]["added_relationships"]==0
    assert result["summary"]["deleted_relationships"]==0
    assert result["comparison_capabilities"]["float"] is False
    assert result["comparison_capabilities"]["logic"] is False
    assert all(x["float_change_hours"] is None for x in result["finish_slippage"])
