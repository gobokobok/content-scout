import math
from dataclasses import dataclass
from decimal import Decimal

from src.config import Settings


@dataclass(frozen=True)
class RunEstimate:
    apify_units: int
    claude_input_tokens: int
    claude_output_tokens: int
    estimated_cost_usd: Decimal
    # D52: the real user-facing token estimate — apify_units (1/publication) plus the flat
    # run-summary base charge — distinct from apify_units itself, which stays a pure Apify-unit
    # count feeding estimated_cost_usd's internal $ math and must not be inflated by a
    # token-currency-only charge.
    estimated_tokens: int


def estimate_run(
    settings: Settings,
    accounts_count: int,
    *,
    duration_days: int | None,
    item_limit: int | None,
) -> RunEstimate:
    if item_limit is not None:
        expected_items = accounts_count * item_limit
    else:
        expected_items = math.ceil(
            accounts_count * (duration_days or 0) * settings.avg_items_per_account_per_day
        )
    apify_units = expected_items
    claude_input_tokens = expected_items * settings.avg_claude_input_tokens_per_item
    claude_output_tokens = expected_items * settings.avg_claude_output_tokens_per_item

    cost = (
        Decimal(apify_units) * Decimal(str(settings.apify_unit_cost_usd))
        + Decimal(claude_input_tokens) * Decimal(str(settings.claude_input_token_cost_usd))
        + Decimal(claude_output_tokens) * Decimal(str(settings.claude_output_token_cost_usd))
    )

    return RunEstimate(
        apify_units=apify_units,
        claude_input_tokens=claude_input_tokens,
        claude_output_tokens=claude_output_tokens,
        estimated_cost_usd=cost.quantize(Decimal("0.0001")),
        estimated_tokens=apify_units + settings.review_base_charge_tokens,
    )
