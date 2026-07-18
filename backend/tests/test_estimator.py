from decimal import Decimal

from src.config import Settings
from src.services.estimator import estimate_run


def test_estimate_scales_with_accounts_and_duration() -> None:
    settings = Settings()
    small = estimate_run(settings, accounts_count=5, duration_days=1)
    large = estimate_run(settings, accounts_count=50, duration_days=7)

    assert large.apify_units > small.apify_units
    assert large.claude_input_tokens > small.claude_input_tokens
    assert large.estimated_cost_usd > small.estimated_cost_usd


def test_estimate_zero_accounts_is_free() -> None:
    settings = Settings()
    est = estimate_run(settings, accounts_count=0, duration_days=7)
    assert est.apify_units == 0
    assert est.estimated_cost_usd == Decimal("0.0000")
