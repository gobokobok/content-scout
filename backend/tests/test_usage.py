from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    KIND_APIFY_RESULT,
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
    UsageEvent,
)
from src.services.usage import rollup_run_totals
from tests.conftest import make_run


async def test_rollup_run_totals_sums_all_kinds_into_cost_and_claude_kinds_into_tokens(
    session: AsyncSession,
) -> None:
    run = await make_run(session)
    session.add_all(
        [
            UsageEvent(
                user_id=run.requested_by,
                run_id=run.id,
                kind=KIND_APIFY_RESULT,
                quantity=10,
                unit_cost_usd=Decimal("0.01"),
            ),
            UsageEvent(
                user_id=run.requested_by,
                run_id=run.id,
                kind=KIND_CLAUDE_INPUT_TOKENS,
                quantity=1000,
                unit_cost_usd=Decimal("0.000001"),
            ),
            UsageEvent(
                user_id=run.requested_by,
                run_id=run.id,
                kind=KIND_CLAUDE_OUTPUT_TOKENS,
                quantity=200,
                unit_cost_usd=Decimal("0.000005"),
            ),
        ]
    )
    await session.commit()

    await rollup_run_totals(session, run)

    assert run.total_input_tokens == 1000
    assert run.total_output_tokens == 200
    # 10*0.01 + 1000*0.000001 + 200*0.000005 = 0.1 + 0.001 + 0.001
    assert run.total_cost_usd == Decimal("0.102000")


async def test_rollup_run_totals_zero_when_no_usage(session: AsyncSession) -> None:
    run = await make_run(session)
    await session.commit()

    await rollup_run_totals(session, run)

    assert run.total_input_tokens == 0
    assert run.total_output_tokens == 0
    assert run.total_cost_usd == Decimal("0")
