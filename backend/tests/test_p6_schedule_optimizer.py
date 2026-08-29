from app.services.p6_schedule_optimizer import build_schedule_optimization_advisor

SAMPLE="""ERMHDR\t8.4\t2026-01-01
%T\tPROJECT
%F\tproj_id\tproj_short_name\tproj_name
%R\t1\tTEST\tRailway
%T\tTASK
%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\tstatus_code\ttask_type\ttarget_drtn_hr_cnt\tremain_drtn_hr_cnt\ttotal_float_hr_cnt\tcstr_type\tclndr_id
%R\t10\t1\t1\tA100\tCritical Work\tTK_NotStart\tTT_Task\t80\t80\t-8\tCS_None\t1
%R\t20\t1\t1\tA200\tFlexible Work\tTK_NotStart\tTT_Task\t200\t200\t120\tCS_None\t1
%R\t30\t1\t1\tM100\tMilestone\tTK_NotStart\tTT_FinMile\t0\t0\t0\tCS_None\t1
%T\tTASKPRED
%F\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt
%R\t30\t10\tPR_FS\t0
%R\t30\t20\tPR_FS\t0
%T\tCALENDAR
%F\tclndr_id\tclndr_name
%R\t1\tStandard
%E
"""

def test_review_priority_is_separate_from_adjustment_potential():
    result=build_schedule_optimization_advisor(SAMPLE.encode(),near_critical_hours=40,long_duration_hours=160)
    rows={x["task_code"]:x for x in result["optimization"]["candidates"]}
    critical=rows["A100"]
    flexible=rows["A200"]
    assert critical["review_priority_score"]>critical["adjustability_score"]
    assert flexible["adjustability_score"]>critical["adjustability_score"]
    assert "Resequencing" in flexible["adjustment_types"]
    assert flexible["adjustment_potential"] in {"Medium","High"}
    assert result["parameter_inventory"]["table_count"]>=4
    assert result["resource_loading"]["status"]=="Not Resource Loaded"
    assert result["resource_loading"]["assignment_count"]==0
