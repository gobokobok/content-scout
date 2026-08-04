import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models import AnalysisRun, ContentItem, DeepAnalysis, DeepAnalysisStatus, RunStatus, User


class RunNotDoneError(Exception):
    pass


class InsufficientTokenBalanceError(Exception):
    pass


def compute_tokens_charged(items_count: int, settings: Settings) -> int:
    """D26 layer-2 / D48: the up-front hold, before extraction has run and the real comment
    counts are known — 1 token per publication + 1 token per comment, assuming every item
    reaches the configured per-post comment target. This is a ceiling, not a guess that has
    to be precise: `deep_analysis_synthesis.py:_reconcile_real_usage` refunds the difference
    down to actual usage once extraction finishes."""
    return items_count * (1 + settings.deep_analysis_comments_per_post)


async def start_deep_analysis(
    session: AsyncSession, run: AnalysisRun, user: User, settings: Settings
) -> DeepAnalysis:
    """Validates + deducts tokens up front, creating the `pending` row. Never enqueues the
    worker pipeline itself — that's the caller's job (E17-S5's endpoint), same separation
    `api/runs.py:create_run` keeps between the DB write and `enqueue_run`.
    """
    if run.status != RunStatus.done:
        raise RunNotDoneError(run.id)

    items_count = await session.scalar(
        select(func.count()).select_from(ContentItem).where(ContentItem.run_id == run.id)
    )
    tokens = compute_tokens_charged(items_count or 0, settings)
    if user.token_balance < tokens:
        raise InsufficientTokenBalanceError(tokens)

    user.token_balance -= tokens
    analysis = DeepAnalysis(
        id=uuid.uuid4(),
        run_id=run.id,
        project_id=run.project_id,
        requested_by=user.id,
        tokens_charged=tokens,
        status=DeepAnalysisStatus.pending,
    )
    session.add(analysis)
    await session.flush()
    return analysis


async def fail_deep_analysis(
    session: AsyncSession, analysis: DeepAnalysis, message: str, *, user_id: uuid.UUID
) -> None:
    """Never leaves a row stuck mid-pipeline (E17-S4 AC) — used by both the extraction and
    synthesis passes on an unrecoverable error. A hard failure delivers zero report, unlike
    E17-S9's thin-coverage path which still delivers a degraded one — so the full up-front
    charge is refunded here, not just reduced."""
    analysis.status = DeepAnalysisStatus.failed
    analysis.error_message = message[:1000]
    analysis.completed_at = datetime.now(UTC)
    if analysis.tokens_charged > 0:
        user = await session.get(User, user_id)
        if user is not None:
            user.token_balance += analysis.tokens_charged
        analysis.tokens_charged = 0
