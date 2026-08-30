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


def test_won_result_with_non_l1_rank_is_flagged_not_silently_corrected():
    warnings=consistency_warnings("Won",2,[{"rank":2,"is_ours":True}])
    assert any("not L1" in x for x in warnings)
    assert len(warnings)>=2


def test_loss_result_does_not_create_false_win_warning():
    assert consistency_warnings("Lost",2,[{"rank":2,"is_ours":True}])==[]
