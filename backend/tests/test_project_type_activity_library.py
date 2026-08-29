from app.services.project_type_activity_library import project_type_activity_library

def test_ohe_project_type_includes_ohe_activity_families():
    rows=project_type_activity_library("Railway OHE Electrification")
    names={x.activity for x in rows}
    assert "OHE foundations" in names
    assert "OHE wiring" in names
    assert "Testing and commissioning" in names

def test_generic_railway_project_returns_cross_discipline_suggestions():
    rows=project_type_activity_library("Railway EPC")
    names={x.activity for x in rows}
    assert "OHE foundations" in names
    assert "PSI equipment installation" in names
    assert "Signalling equipment installation" in names
