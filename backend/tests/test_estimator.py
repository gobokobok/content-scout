from decimal import Decimal

from src.config import Settings
from src.services.estimator import estimate_run


def test_estimate_scales_with_accounts_and_duration() -> None:
    settings = Settings()
    small = estimate_run(settings, accounts_count=5, duration_days=1, item_limit=None)
    large = estimate_run(settings, accounts_count=50, duration_days=7, item_limit=None)

    assert large.apify_units > small.apify_units
    assert large.claude_input_tokens > small.claude_input_tokens
    assert large.estimated_cost_usd > small.estimated_cost_usd


def test_estimate_zero_accounts_is_free() -> None:
    settings = Settings()
    est = estimate_run(settings, accounts_count=0, duration_days=7, item_limit=None)
    assert est.apify_units == 0
    assert est.estimated_cost_usd == Decimal("0.0000")


def test_estimate_by_item_limit_scales_with_accounts_and_limit() -> None:
    settings = Settings()
    small = estimate_run(settings, accounts_count=5, duration_days=None, item_limit=5)
    large = estimate_run(settings, accounts_count=50, duration_days=None, item_limit=50)

    assert large.apify_units > small.apify_units
    assert small.apify_units == 25
    assert large.apify_units == 2500


def test_estimate_tokens_includes_base_charge_distinct_from_apify_units() -> None:
    """D52: estimated_tokens is the real user-facing token estimate — apify_units plus the
    flat run-summary base charge — not the same value as apify_units, which stays a pure
    Apify-unit count feeding estimated_cost_usd's internal $ math."""
    settings = Settings(review_base_charge_tokens=5)
    est = estimate_run(settings, accounts_count=5, duration_days=None, item_limit=5)

    assert est.apify_units == 25
    assert est.estimated_tokens == 30
