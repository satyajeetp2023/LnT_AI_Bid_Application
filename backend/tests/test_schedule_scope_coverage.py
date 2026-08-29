from app.services.schedule_scope_coverage import _terms,_is_blocking,_lifecycle_stages

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
