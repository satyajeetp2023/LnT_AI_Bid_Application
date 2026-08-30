from types import SimpleNamespace
from decimal import Decimal
from app.services.drawing_boq_verification import _boq_data,_match_score,_unit

def test_drawing_scope_match_prefers_same_item_terms():
    observation=SimpleNamespace(item_name="OHE mast erection",item_category="OHE")
    boq={"description":"Supply and erection of OHE mast"}
    assert _match_score(observation,boq)>=.35

def test_boq_quantity_evidence_is_parsed():
    item=SimpleNamespace(
        source_excerpt="BOQ 12.4: Supply and erection of OHE mast | Qty: 250 Nos",
        source_reference="12.4",activity_name="OHE mast",
    )
    parsed=_boq_data(item)
    assert parsed["reference"]=="12.4"
    assert parsed["quantity"]==Decimal("250")
    assert _unit(parsed["unit"])=="nos"

def test_unit_normalization_handles_common_variants():
    assert _unit("No")=="nos"
    assert _unit("Metres")=="m"
    assert _unit("Cu M")=="m3"
