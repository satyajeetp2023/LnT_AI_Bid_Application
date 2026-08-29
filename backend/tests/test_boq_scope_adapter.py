from app.services.boq_scope_adapter import _phases,_terms

def test_compound_boq_item_decomposes_lifecycle_phases():
    text="Design, manufacture, supply, install, test and commission traction equipment"
    phases=_phases(text)
    assert "Design" in phases
    assert "Procurement / Supply" in phases
    assert "Installation / Erection" in phases
    assert "Testing" in phases
    assert "Commissioning" in phases

def test_boq_terms_keep_scope_specific_words():
    words=_terms("Supply and installation of 25 kV OHE mast and portal equipment")
    assert "ohe" in words
    assert "mast" in words
    assert "portal" in words
    assert "supply" not in words
