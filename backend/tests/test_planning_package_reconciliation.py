from app.services.planning_package_reconciliation import _score


def test_resource_activity_matching_is_scope_sensitive():
    assert _score("OHE mast erection section A","A200 OHE mast erection")>.55
    assert _score("OHE mast erection","Bridge foundation")<.34


def test_work_front_terms_help_resource_matching():
    assert _score("Section A mast erection","A100 mast erection section A")>.55
