from app.services.p6_schedule_comparison import compare_xer

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
    assert result["finish_slippage"][0]["finish_variance_days"]>=5
