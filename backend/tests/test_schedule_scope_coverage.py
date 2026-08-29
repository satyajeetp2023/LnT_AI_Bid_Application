from app.services.schedule_scope_coverage import _terms,_is_blocking,_lifecycle_stages,_activity_search_index,_match

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
