from types import SimpleNamespace
from app.services.clause_risk_intelligence import _risk_matches

def pattern(signals,exclusions=()):
    return SimpleNamespace(pattern_terms=list(signals),exclusion_terms=list(exclusions))

def test_unlimited_liability_pattern_matches():
    matched,confidence=_risk_matches(
        "The Contractor's liability shall be unlimited.",
        pattern(["liability shall be unlimited"],["aggregate liability shall not exceed"]),
    )
    assert matched is True
    assert confidence>=.70

def test_liability_cap_exclusion_suppresses_false_flag():
    matched,_=_risk_matches(
        "The aggregate liability shall not exceed 10% of the Contract Price.",
        pattern(["liability"],["aggregate liability shall not exceed"]),
    )
    assert matched is False
