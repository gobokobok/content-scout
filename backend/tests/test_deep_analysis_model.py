from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models import DeepAnalysis, DeepAnalysisStatus
from src.services.deep_analysis import (
    charge_tokens_for_item,
    create_pending_deep_analysis,
    estimate_deep_analysis_tokens,
    fail_deep_analysis,
)
from tests.conftest import make_project, make_run, make_user


def _settings(**overrides) -> Settings:
    overrides.setdefault("deep_analysis_comments_per_post", 9)  # -> 10 tokens/item ceiling
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


def test_estimate_tokens_account_mode_item_limit() -> None:
    settings = _settings(deep_analysis_comments_per_post=4)
    assert (
        estimate_deep_analysis_tokens(
            settings, analysis_mode="account", duration_days=None, item_limit=3, comments_limit=None
        )
        == 15  # 3 items * (1 + 4)
    )


def test_estimate_tokens_account_mode_duration_days() -> None:
    settings = _settings(deep_analysis_comments_per_post=4, avg_items_per_account_per_day=1.0)
    assert (
        estimate_deep_analysis_tokens(
            settings, analysis_mode="account", duration_days=5, item_limit=None, comments_limit=None
        )
        == 25  # ceil(5 * 1.0) items * (1 + 4)
    )


def test_estimate_tokens_post_mode_is_always_one_item() -> None:
    settings = _settings(deep_analysis_comments_per_post=25)
    assert (
        estimate_deep_analysis_tokens(
            settings, analysis_mode="post", duration_days=None, item_limit=None, comments_limit=None
        )
        == 26  # 1 + 25
    )
    # post mode's own comments_limit overrides the account-mode default.
    assert (
        estimate_deep_analysis_tokens(
            settings, analysis_mode="post", duration_days=None, item_limit=None, comments_limit=10
        )
        == 11
    )


async def test_create_pending_deep_analysis_charges_nothing_up_front(
    session: AsyncSession,
) -> None:
    user = await make_user(session, token_balance=100)
    run = await make_run(session, requested_by=user)

    analysis = await create_pending_deep_analysis(session, run, user)

    assert analysis.status == DeepAnalysisStatus.pending
    assert analysis.tokens_charged == 0
    assert analysis.run_id == run.id
    assert analysis.project_id == run.project_id
    assert user.token_balance == 100  # untouched — D50 incremental charging


async def test_charge_tokens_for_item_deducts_publication_plus_comments(
    session: AsyncSession,
) -> None:
    user = await make_user(session, token_balance=100)
    run = await make_run(session, requested_by=user)
    analysis = await create_pending_deep_analysis(session, run, user)

    charged = charge_tokens_for_item(analysis, user, comments_analyzed_count=4)

    assert charged is True
    assert analysis.tokens_charged == 5  # 1 + 4
    assert user.token_balance == 95


async def test_charge_tokens_for_item_caps_at_remaining_balance(session: AsyncSession) -> None:
    user = await make_user(session, token_balance=3)
    run = await make_run(session, requested_by=user)
    analysis = await create_pending_deep_analysis(session, run, user)

    charged = charge_tokens_for_item(analysis, user, comments_analyzed_count=10)

    assert charged is True
    assert user.token_balance == 0
    assert analysis.tokens_charged == 3  # capped, never goes negative


async def test_charge_tokens_for_item_returns_false_when_already_exhausted(
    session: AsyncSession,
) -> None:
    user = await make_user(session, token_balance=0)
    run = await make_run(session, requested_by=user)
    analysis = await create_pending_deep_analysis(session, run, user)

    charged = charge_tokens_for_item(analysis, user, comments_analyzed_count=2)

    assert charged is False
    assert analysis.tokens_charged == 0
    assert user.token_balance == 0


async def test_fail_deep_analysis_does_not_refund(session: AsyncSession) -> None:
    # D50: tokens_charged always already reflects real completed work under incremental
    # charging, so a failure has nothing artificial left to refund (unlike the old up-front
    # lump-sum model).
    user = await make_user(session, token_balance=50)
    run = await make_run(session, requested_by=user)
    analysis = await create_pending_deep_analysis(session, run, user)
    charge_tokens_for_item(analysis, user, comments_analyzed_count=4)
    balance_before = user.token_balance

    await fail_deep_analysis(session, analysis, "boom", user_id=user.id)

    assert analysis.status == DeepAnalysisStatus.failed
    assert analysis.error_message == "boom"
    assert analysis.completed_at is not None
    assert analysis.tokens_charged == 5
    assert user.token_balance == balance_before
