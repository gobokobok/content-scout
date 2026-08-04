import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models import DeepAnalysis, DeepAnalysisStatus, RunStatus
from src.services.deep_analysis import (
    InsufficientTokenBalanceError,
    RunNotDoneError,
    compute_tokens_charged,
    start_deep_analysis,
)
from tests.conftest import make_content_item, make_project, make_run, make_user


def _settings(**overrides) -> Settings:
    overrides.setdefault("deep_analysis_comments_per_post", 9)  # -> 10 tokens/item held
    return Settings(**overrides)


async def test_deep_analysis_roundtrip_and_defaults(session: AsyncSession) -> None:
    user = await make_user(session)
    project = await make_project(session)
    run = await make_run(session, project=project, requested_by=user)

    analysis = DeepAnalysis(
        run_id=run.id, project_id=project.id, requested_by=user.id, tokens_charged=42
    )
    session.add(analysis)
    await session.flush()
    await session.refresh(analysis)

    assert analysis.status == DeepAnalysisStatus.pending
    assert analysis.report_stats is None
    assert analysis.report_recommendations is None
    assert analysis.completed_at is None


def test_compute_tokens_charged_is_one_per_item_plus_configured_comments_ceiling() -> None:
    # D48: 1 token/item + 1 token/comment, holding for the configured per-post comment target.
    settings = _settings(deep_analysis_comments_per_post=4)
    assert compute_tokens_charged(3, settings) == 15  # 3 items * (1 + 4)
    assert compute_tokens_charged(0, settings) == 0


async def test_start_deep_analysis_requires_done_run(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user, duration_days=3)
    run.status = RunStatus.scraping

    with pytest.raises(RunNotDoneError):
        await start_deep_analysis(session, run, user, _settings())


async def test_start_deep_analysis_rejects_insufficient_balance(session: AsyncSession) -> None:
    user = await make_user(session, token_balance=1)
    run = await make_run(session, requested_by=user, duration_days=3)
    run.status = RunStatus.done
    await make_content_item(session, run=run)

    with pytest.raises(InsufficientTokenBalanceError):
        await start_deep_analysis(session, run, user, _settings())

    assert user.token_balance == 1  # untouched on rejection


async def test_start_deep_analysis_deducts_tokens_and_creates_pending_row(
    session: AsyncSession,
) -> None:
    user = await make_user(session, token_balance=100)
    run = await make_run(session, requested_by=user, duration_days=3)
    run.status = RunStatus.done
    await make_content_item(session, run=run)
    await make_content_item(session, run=run)

    analysis = await start_deep_analysis(session, run, user, _settings())

    assert analysis.status == DeepAnalysisStatus.pending
    assert analysis.tokens_charged == 20  # 2 items * (1 + 9)
    assert analysis.run_id == run.id
    assert analysis.project_id == run.project_id
    assert user.token_balance == 80
