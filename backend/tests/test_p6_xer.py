from app.services.p6_xer import analyze_xer,parse_xer


SAMPLE="""ERMHDR\t8.4\t2026-08-29
%T\tPROJECT
%F\tproj_id\tproj_short_name\tproj_name\tlast_recalc_date\tplan_start_date\tplan_end_date
%R\t1\tTEST\tTest Railway Project\t2026-08-20 08:00\t2026-01-01 08:00\t2027-01-01 17:00
%T\tPROJWBS
%F\twbs_id\tproj_id\twbs_short_name\twbs_name
%R\t10\t1\tWBS1\tMain Works
%T\tTASK
%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\tstatus_code\ttask_type\ttarget_drtn_hr_cnt\tremain_drtn_hr_cnt\ttotal_float_hr_cnt\tcstr_type\tact_start_date\tact_end_date
%R\t100\t1\t10\tA100\tStart Work\tTK_Active\tTT_Task\t80\t40\t16\tCS_None\t2026-08-01 08:00\t
%R\t200\t1\t10\tA200\tCritical Work\tTK_NotStart\tTT_Task\t240\t240\t-8\tCS_MSO\t\t
%R\t300\t1\t10\tA300\tOpen Activity\tTK_NotStart\tTT_Task\t40\t40\t24\tCS_None\t\t
%T\tTASKPRED
%F\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt
%R\t200\t100\tPR_FS\t8
%E
"""


def test_parse_xer_tables():
    tables=parse_xer(SAMPLE.encode())
    assert set(["PROJECT","PROJWBS","TASK","TASKPRED"])<=set(tables)
    assert len(tables["TASK"])==3


def test_schedule_health_flags_open_ends_float_constraints_and_lag():
    result=analyze_xer(SAMPLE.encode(),long_duration_hours=160)
    assert result["project"]["project_code"]=="TEST"
    assert result["counts"]["activities"]==3
    assert result["health"]["issue_counts"]["negative_float"]==1
    assert result["health"]["issue_counts"]["constraints"]==1
    assert result["health"]["issue_counts"]["long_duration"]==1
    assert result["health"]["issue_counts"]["lagged_relationships"]==1
    assert result["health"]["issue_counts"]["open_start"]>=1
    assert result["health"]["issue_counts"]["open_finish"]>=1
