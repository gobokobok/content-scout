from typing import Any, Literal

from sqlalchemy import Float, case, cast, func
from sqlalchemy.sql.elements import ColumnElement

from src.config import Settings
from src.models import Account, ContentItem

# Derived at read time from published_at/now() (per ARCHITECTURE.md) — always fresh, sortable
# server-side, no column to keep in sync. Consumed by the results table query (E5-S1).

MIN_DAYS_DIVISOR = 1.0 / 24  # clamp to 1 hour so a just-published item doesn't divide by ~0

VIRALITY_BUCKETS = ("high", "medium", "low")


def days_since_published_expr() -> ColumnElement[float]:
    return func.greatest(
        func.extract("epoch", func.now() - ContentItem.published_at) / 86400.0, 0.0
    )


def _per_day_expr(column: Any) -> ColumnElement[Any]:
    divisor = func.greatest(days_since_published_expr(), MIN_DAYS_DIVISOR)
    return case((column.is_(None), None), else_=column / divisor)


def views_per_day_expr() -> ColumnElement[Any]:
    return _per_day_expr(ContentItem.views)


def likes_per_day_expr() -> ColumnElement[Any]:
    return _per_day_expr(ContentItem.likes)


def _engagement_expr() -> ColumnElement[Any]:
    """likes + comments, NULL-safe. Shared by the virality ratio and engagement_rate."""
    return cast(func.coalesce(ContentItem.likes, 0) + func.coalesce(ContentItem.comments, 0), Float)


def virality_ratio_expr() -> ColumnElement[Any]:
    """E5-S5: how hard this item outperformed *that account's own* median within the run —
    never an absolute/cross-account threshold (a meme account and a niche B2B account have
    wildly different normal engagement). `NULLIF`/`GREATEST` NULL-handling notes:
    - `NULLIF(median, 0)` avoids a division-by-zero crash for an all-zero-engagement account;
      the ratio comes back NULL in that edge case, which the bucketer treats as "no badge"
      alongside the too-few-items case, rather than inventing a fake infinite ratio.
    - Postgres `GREATEST` ignores NULL arguments (only NULL if *every* argument is NULL), so a
      non-reel item (view_ratio always NULL) cleanly falls back to its engagement_ratio alone.
    """
    engagement = _engagement_expr()
    median_engagement = (
        func.percentile_cont(0.5).within_group(engagement).over(partition_by=ContentItem.account_id)
    )
    engagement_ratio = engagement / func.nullif(median_engagement, 0)

    reel_views = case((ContentItem.views.isnot(None), cast(ContentItem.views, Float)), else_=None)
    median_views = (
        func.percentile_cont(0.5).within_group(reel_views).over(partition_by=ContentItem.account_id)
    )
    view_ratio = case(
        (
            ContentItem.views.isnot(None),
            cast(ContentItem.views, Float) / func.nullif(median_views, 0),
        ),
        else_=None,
    )

    return func.greatest(engagement_ratio, view_ratio)


def account_item_count_expr() -> ColumnElement[int]:
    """Items for this item's account within the current run's result set (window over the
    query's WHERE run_id == ... — see items.py/export.py). Backs the `virality_min_items` guard."""
    return func.count().over(partition_by=ContentItem.account_id)


def engagement_rate_expr() -> ColumnElement[Any]:
    """(likes + comments) / followers — cross-account comparison, separate from the
    self-relative virality badge above. Requires the E5-S4 follower join (Account.followers_count).
    """
    return _engagement_expr() / cast(func.nullif(Account.followers_count, 0), Float)


def bucket_virality(
    ratio: float | None, item_count: int, settings: Settings
) -> Literal["high", "medium", "low"] | None:
    """Pure function so thresholds are unit-testable without a database."""
    if item_count < settings.virality_min_items or ratio is None:
        return None
    if ratio >= settings.virality_high_ratio:
        return "high"
    if ratio < settings.virality_low_ratio:
        return "low"
    return "medium"
