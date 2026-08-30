from app.services.schedule_scope_coverage import _terms,_is_blocking,_lifecycle_stages,_activity_search_index,_match,_consolidate_rows

class Dummy:
    mandatory=True
    coverage_status="Missing"
    disposition_status="Unexplained"

def test_missing_mandatory_activity_blocks_until_explained():
    item=Dummy()
    assert _is_blocking(item) is True
    item.disposition_status="To Be Added"
    assert _is_blocking(item) is True
    item.disposition_status="Covered Elsewhere"
    assert _is_blocking(item) is False

def test_scope_matching_terms_ignore_generic_words():
    words=_terms("Contractor shall install overhead equipment and test section")
    assert "install" in words
    assert "overhead" in words
    assert "contractor" not in words


def test_contract_lifecycle_decomposition():
    stages=_lifecycle_stages("Contractor shall design, supply, install, test and commission the system")
    assert "Design" in stages
    assert "Procurement / Supply" in stages
    assert "Construction / Installation" in stages
    assert "Testing" in stages
    assert "Commissioning" in stages


class ScopeDummy:
    activity_name="OHE mast erection"
    match_keywords=["ohe","mast","erection"]


def test_scope_match_uses_wbs_context_when_task_name_is_abbreviated():
    tables={
        "PROJWBS":[{"wbs_id":"1","wbs_name":"OHE Works","parent_wbs_id":""}],
        "TASK":[{"task_id":"10","task_code":"A100","task_name":"Mast ER","wbs_id":"1"}],
        "TASKACTV":[],
        "ACTVCODE":[],
        "ACTVTYPE":[],
    }
    index=_activity_search_index(tables)
    task,score,candidates=_match(ScopeDummy(),index)
    assert task["task_code"]=="A100"
    assert score>=0.25
    assert candidates[0]["wbs_path"]=="OHE Works"


def test_cross_source_duplicate_scope_consolidates():
    rows=[
        {"id":1,"activity_name":"OHE mast erection","activity_level":"Activity","source_type":"Contract / Technical Requirement","source_reference":"Cl. 10","mandatory":True,"blocking":True,"coverage_status":"Missing","disposition_status":"Unexplained","why_expected":"contract"},
        {"id":2,"activity_name":"OHE mast erection","activity_level":"Activity","source_type":"Project-Type Knowledge","source_reference":"Railway OHE","mandatory":False,"blocking":False,"coverage_status":"Missing","disposition_status":"Unexplained","why_expected":"knowledge"},
    ]
    groups=_consolidate_rows(rows)
    assert len(groups)==1
    assert groups[0]["evidence_count"]==2
    assert groups[0]["canonical_item_id"]==1


def test_distinct_boq_references_do_not_consolidate():
    rows=[
        {"id":1,"activity_name":"OHE mast erection","activity_level":"BOQ Scope","source_type":"BOQ","source_reference":"BOQ:1","mandatory":True,"blocking":True,"coverage_status":"Missing","disposition_status":"Unexplained","why_expected":"boq 1"},
        {"id":2,"activity_name":"OHE mast erection","activity_level":"BOQ Scope","source_type":"BOQ","source_reference":"BOQ:2","mandatory":True,"blocking":True,"coverage_status":"Missing","disposition_status":"Unexplained","why_expected":"boq 2"},
    ]
    groups=_consolidate_rows(rows)
    assert len(groups)==2


def test_scope_catalog_has_no_unbound_reverse_coverage_state():
    # The independent scope catalog has no uploaded schedule context, so reverse
    # coverage must remain zero rather than referencing evaluation-only state.
    source=__import__("inspect").getsource(schedule_scope_catalog)
    assert "len(unmapped)" not in source
    assert '"unmapped_schedule_activities":0' in source
