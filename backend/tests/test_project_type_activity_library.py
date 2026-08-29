from app.services.project_type_activity_library import project_type_activity_library

def test_ohe_project_type_includes_ohe_activity_families():
    rows=project_type_activity_library("Railway OHE Electrification")
    names={x.activity for x in rows}
    assert "OHE foundations" in names
    assert "OHE wiring" in names
    assert "Testing and commissioning" in names

def test_generic_railway_project_does_not_assume_every_discipline():
    rows=project_type_activity_library("Railway EPC")
    names={x.activity for x in rows}
    assert "Project mobilization and site establishment" in names
    assert "OHE foundations" not in names
    assert "PSI equipment installation" not in names

def test_scope_text_activates_relevant_disciplines():
    rows=project_type_activity_library("Railway EPC","25 kV OHE catenary, traction substation and SCADA RTU works")
    names={x.activity for x in rows}
    assert "OHE foundations" in names
    assert "PSI equipment installation" in names
    assert "SCADA field installation" in names
    assert "Signalling equipment installation" not in names
