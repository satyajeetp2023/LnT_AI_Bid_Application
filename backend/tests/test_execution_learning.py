from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services.execution_learning import execution_metrics


def test_execution_metrics_compare_only_supported_bid_and_actual_values():
    bid=SimpleNamespace(our_bid_value=Decimal("1000"),our_margin_percent=Decimal("8.5"))
    actual=SimpleNamespace(
        final_contract_value=Decimal("1150"),actual_cost=Decimal("1035"),final_margin_percent=Decimal("10.0"),
        approved_variations=Decimal("100"),claims_recovered=Decimal("25"),eot_days=45,
        actual_start_date=date(2024,1,1),actual_completion_date=date(2025,1,1),
    )
    metrics=execution_metrics(bid,actual)
    assert metrics["revenue_change_vs_bid"]==150.0
    assert metrics["revenue_change_vs_bid_percent"]==15.0
    assert metrics["margin_change_percentage_points"]==1.5
    assert metrics["actual_duration_days"]==366
    assert metrics["cost_to_final_value_percent"]==90.0
    assert metrics["variation_share_percent"]==8.7
    assert metrics["claims_recovered_share_percent"]==2.17


def test_execution_metrics_keep_missing_actuals_unknown():
    bid=SimpleNamespace(our_bid_value=Decimal("1000"),our_margin_percent=None)
    metrics=execution_metrics(bid,None)
    assert metrics["revenue_change_vs_bid"] is None
    assert metrics["margin_change_percentage_points"] is None
    assert metrics["actual_duration_days"] is None
