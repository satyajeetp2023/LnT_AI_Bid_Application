from types import SimpleNamespace

from app.services.historical_bid_comparison import similarity_score


def bid(**overrides):
    values={
        "project_type":"OHE",
        "client":"DFCCIL",
        "contract_type":"EPC",
        "location":"Gujarat",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_similarity_score_weights_exact_normalized_fields():
    score,fields=similarity_score(
        bid(),
        bid(client=" dfccil ",location="GUJARAT"),
    )
    assert score==100
    assert set(fields)=={"project_type","client","contract_type","location"}


def test_similarity_does_not_claim_match_on_different_scope_fields():
    score,fields=similarity_score(
        bid(),
        bid(project_type="Metro",client="DMRC",contract_type="Item Rate",location="Delhi"),
    )
    assert score==0
    assert fields==[]


def test_similarity_ignores_missing_location_instead_of_inventing_match():
    score,fields=similarity_score(
        bid(location=None),
        bid(location=None),
    )
    assert score==85
    assert "location" not in fields
