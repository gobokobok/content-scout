from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
    AnalysisRun,
    UsageEvent,
)


async def rollup_run_totals(session: AsyncSession, run: AnalysisRun) -> None:
    """Sums every usage_events row for the run onto its total_* columns (all kinds contribute
    to total_cost_usd; only Claude kinds contribute to total_{input,output}_tokens)."""
    stmt = (
        select(
            UsageEvent.kind,
            func.sum(UsageEvent.quantity),
            func.sum(UsageEvent.quantity * UsageEvent.unit_cost_usd),
        )
        .where(UsageEvent.run_id == run.id)
        .group_by(UsageEvent.kind)
    )

    total_cost = Decimal("0")
    total_input_tokens = 0
    total_output_tokens = 0
    for kind, quantity_sum, cost_sum in await session.execute(stmt):
        total_cost += cost_sum or Decimal("0")
        if kind == KIND_CLAUDE_INPUT_TOKENS:
            total_input_tokens = int(quantity_sum or 0)
        elif kind == KIND_CLAUDE_OUTPUT_TOKENS:
            total_output_tokens = int(quantity_sum or 0)

    run.total_cost_usd = total_cost
    run.total_input_tokens = total_input_tokens
    run.total_output_tokens = total_output_tokens
