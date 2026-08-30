from app.services.planning_package_reconciliation import _finding_candidates,_overlap,_productivity_capacity,_score


def test_resource_activity_matching_is_scope_sensitive():
    assert _score("OHE mast erection section A","A200 OHE mast erection")>.55
    assert _score("OHE mast erection","Bridge foundation")<.34


def test_work_front_terms_help_resource_matching():
    assert _score("Section A mast erection","A100 mast erection section A")>.55


def test_planning_findings_are_created_for_uncovered_and_contract_staff_gaps():
    analysis={
        "issues":[{"severity":"High","type":"Missing Staff Plan","message":"No bidder Staff Plan has been identified."}],
        "activity_resource_coverage":[
            {"task_code":"A100","task_id":"1","task_name":"Foundation","coverage_status":"Uncovered"}
        ],
        "separate_plan_matching":[],
        "staff_plan":{"missing_contract_required_roles":["Planning Manager"]},
    }
    findings=_finding_candidates(analysis)
    keys={x["finding_key"] for x in findings}
    assert "issue:missing-staff-plan" in keys
    assert "uncovered-activity:A100" in keys
    assert "contract-staff:planning-manager" in keys


def test_resource_timing_misalignment_becomes_reviewable_finding():
    analysis={
        "issues":[],
        "activity_resource_coverage":[],
        "separate_plan_matching":[{
            "id":7,"timeline_status":"Starts After Activity","match_status":"Matched",
            "resource_name":"Crane","matched_task_code":"A200","matched_task_name":"Mast Erection",
            "activity_reference":"Mast Erection","work_front":None,
        }],
        "staff_plan":{"missing_contract_required_roles":[]},
    }
    findings=_finding_candidates(analysis)
    assert findings[0]["finding_key"]=="resource-timing:7"
    assert findings[0]["severity"]=="Medium"


def test_bidder_productivity_capacity_uses_resource_quantity_only_when_basis_is_per_resource():
    class Entry:
        productivity_rate=8
        productivity_unit="Nos/Crew/Day"
        quantity=3
    result=_productivity_capacity(Entry())
    assert result["capacity_per_day"]==24
    assert result["basis"]=="Per Resource × Quantity"


def test_total_bidder_productivity_rate_is_not_multiplied_by_resource_quantity():
    class Entry:
        productivity_rate=20
        productivity_unit="Nos/Day"
        quantity=3
    result=_productivity_capacity(Entry())
    assert result["capacity_per_day"]==20
    assert result["basis"]=="Total Planned Rate"


def test_overlap_only_when_activity_periods_intersect():
    from datetime import date
    assert _overlap(date(2026,1,1),date(2026,1,10),date(2026,1,8),date(2026,1,20)) is True
    assert _overlap(date(2026,1,1),date(2026,1,5),date(2026,1,6),date(2026,1,20)) is False


def test_per_resource_shortfall_math_supports_minimum_resource_quantity():
    class Entry:
        productivity_rate=8
        productivity_unit="Nos/Crew/Day"
        quantity=2
    capacity=_productivity_capacity(Entry())
    required_rate=20
    minimum=__import__("math").ceil(required_rate/capacity["rate"])
    assert minimum==3
    assert minimum-int(capacity["resource_quantity"])==1


def test_contract_staff_phase_timing_gap_becomes_reviewable_finding():
    analysis={
        "issues":[{"severity":"High","type":"Staff Phase Timing","message":"1 contract-required staff deployment entry does not cover the matching schedule phase window."}],
        "activity_resource_coverage":[],
        "separate_plan_matching":[],
        "staff_plan":{"missing_contract_required_roles":[]},
    }
    findings=_finding_candidates(analysis)
    assert findings[0]["finding_key"]=="issue:staff-phase-timing"
    assert findings[0]["severity"]=="High"
    assert findings[0]["finding_type"]=="Staff Phase Timing"
