import pytest
from pydantic import ValidationError
from app.schemas.historical_bids import BidOutcomeUpsert

from app.services.historical_bid_intelligence import consistency_warnings,price_summary


def test_price_summary_exposes_l1_to_l4_and_our_gap():
    rows=[
        {"bidder_name":"A","rank":1,"bid_value":100.0,"currency":"INR","is_ours":False},
        {"bidder_name":"L&T","rank":2,"bid_value":108.0,"currency":"INR","is_ours":True},
        {"bidder_name":"C","rank":3,"bid_value":115.0,"currency":"INR","is_ours":False},
        {"bidder_name":"D","rank":4,"bid_value":121.0,"currency":"INR","is_ours":False},
    ]
    result=price_summary(rows)
    assert len(result["l1_to_l4"])==4
    assert result["our_gap_to_l1"]==8.0
    assert result["our_gap_to_l1_percent"]==8.0


def test_price_summary_exposes_descriptive_market_spread():
    rows=[
        {"bidder_name":"A","rank":1,"bid_value":100.0,"currency":"INR","is_ours":False},
        {"bidder_name":"B","rank":2,"bid_value":105.0,"currency":"INR","is_ours":False},
        {"bidder_name":"C","rank":3,"bid_value":110.0,"currency":"INR","is_ours":False},
        {"bidder_name":"D","rank":4,"bid_value":120.0,"currency":"INR","is_ours":False},
    ]
    spread=price_summary(rows)["market_spread"]
    assert spread["l2_to_l1_percent"]==5.0
    assert spread["l3_to_l1_percent"]==10.0
    assert spread["l4_to_l1_percent"]==20.0
    assert spread["recorded_bidders"]==4


def test_market_spread_does_not_invent_missing_rank_values():
    rows=[{"bidder_name":"A","rank":1,"bid_value":100.0,"currency":"INR","is_ours":False}]
    spread=price_summary(rows)["market_spread"]
    assert spread["l2_to_l1_percent"] is None
    assert spread["l3_to_l1_percent"] is None
    assert spread["l4_to_l1_percent"] is None


def test_won_result_with_non_l1_rank_is_flagged_not_silently_corrected():
    warnings=consistency_warnings("Won",2,[{"rank":2,"is_ours":True}])
    assert any("not L1" in x for x in warnings)
    assert len(warnings)>=2


def test_loss_result_does_not_create_false_win_warning():
    assert consistency_warnings("Lost",2,[{"rank":2,"is_ours":True}])==[]


def test_competitor_metrics_are_descriptive_from_recorded_rows():
    from collections import Counter
    ranks=Counter({"A":6})
    appearances=Counter({"A":3})
    wins=Counter({"A":1})
    assert round(wins["A"]*100/appearances["A"],1)==33.3
    assert round(ranks["A"]/appearances["A"],2)==2.0


def test_bidder_duplicate_validation_normalizes_case_and_whitespace():
    with pytest.raises(ValidationError):
        BidOutcomeUpsert(
            result_status="Lost",
            prices=[
                {"bidder_name":"ABC Ltd","rank":1,"bid_value":100},
                {"bidder_name":" abc   ltd ","rank":2,"bid_value":110},
            ],
        )
