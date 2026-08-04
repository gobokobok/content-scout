import math
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models import AnalysisRun, DeepAnalysis, DeepAnalysisStatus, User


class InsufficientTokenBalanceError(Exception):
    pass


def estimate_deep_analysis_tokens(
    settings: Settings,
    *,
    analysis_mode: str,
    duration_days: int | None,
    item_limit: int | None,
    comments_limit: int | None,
) -> int:
    """D50: a pre-confirm ceiling estimate for the ru UI, not a charge — real cost is billed
    incrementally per item as extraction actually happens (see charge_tokens_for_item), plus a
    flat base charge for the run's one synthesis call (D51, see synthesize_report). Mirrors
    estimator.py's expected-items heuristic for account mode; post mode is always exactly 1 item."""
    per_post_comments = comments_limit or settings.deep_analysis_comments_per_post
    if analysis_mode == "post":
        return settings.deep_analysis_base_charge_tokens + 1 + per_post_comments
    if item_limit is not None:
        expected_items = item_limit
    else:
        expected_items = math.ceil((duration_days or 0) * settings.avg_items_per_account_per_day)
    return settings.deep_analysis_base_charge_tokens + expected_items * (1 + per_post_comments)


async def create_pending_deep_analysis(
    session: AsyncSession, run: AnalysisRun, user: User
) -> DeepAnalysis:
    """Creates the `pending` row with no charge yet (D50) — extraction charges incrementally,
    per item, as real work happens (see charge_tokens_for_item), and a flat base charge is
    applied once synthesis is attempted (D51, see deep_analysis_synthesis.py:synthesize_report).
    The caller (worker.py) is responsible for the whole scrape->extract->synthesize pipeline;
    this just marks the start."""
    analysis = DeepAnalysis(
        id=uuid.uuid4(),
        run_id=run.id,
        project_id=run.project_id,
        requested_by=user.id,
        tokens_charged=0,
        status=DeepAnalysisStatus.pending,
    )
    session.add(analysis)
    await session.flush()
    return analysis


def charge_tokens_for_item(
    analysis: DeepAnalysis, user: User, *, comments_analyzed_count: int
) -> bool:
    """D50 incremental charging: 1 token for the publication + 1 per comment actually analyzed,
    mirroring process_run's per-batch token_balance check-and-stop pattern. Returns False (and
    charges nothing) when the balance is already exhausted, so the caller can stop extracting
    further items rather than driving the balance negative. Does not include the D51 base
    charge for the run's synthesis call — that's applied separately, once, in
    deep_analysis_synthesis.py:synthesize_report."""
    if user.token_balance <= 0:
        return False
    cost = 1 + comments_analyzed_count
    charge = min(cost, user.token_balance)
    user.token_balance -= charge
    analysis.tokens_charged += charge
    return True


async def fail_deep_analysis(
    session: AsyncSession, analysis: DeepAnalysis, message: str, *, user_id: uuid.UUID
) -> None:
    """Never leaves a row stuck mid-pipeline (E17-S4 AC). Under D50's incremental-charging
    model tokens_charged always already reflects real completed work at the point of failure —
    unlike the old up-front lump-sum model, there is nothing artificial left to refund here."""
    analysis.status = DeepAnalysisStatus.failed
    analysis.error_message = message[:1000]
    analysis.completed_at = datetime.now(UTC)
