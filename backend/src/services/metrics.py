from typing import Any, Literal

from sqlalchemy import Float, Subquery, case, cast, func, select
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
    """likes + comments, NULL-safe. Shared by the virality baseline and engagement_rate."""
    return cast(func.coalesce(ContentItem.likes, 0) + func.coalesce(ContentItem.comments, 0), Float)


def engagement_rate_expr() -> ColumnElement[Any]:
    """(likes + comments) / followers — cross-account comparison, separate from the
    self-relative virality badge below. Requires the E5-S4 follower join (Account.followers_count).
    """
    return _engagement_expr() / cast(func.nullif(Account.followers_count, 0), Float)


def virality_baseline_subquery(item_filter: ColumnElement[bool]) -> Subquery:
    """E5-S5: per-account median engagement/views + item count within a run, one row per
    (run_id, account_id) — join this onto the item query (by run_id + account_id) rather than
    using a window function. Postgres does not support `OVER` for ordered-set aggregates like
    `percentile_cont` (only plain `GROUP BY` aggregation), so the per-account baseline has to
    be computed as its own grouped subquery and joined back onto each item.

    Grouped by run_id too (not just account_id) so this same function covers both a single-run
    query (item_filter = ContentItem.run_id == run_id) and a cross-run project query — a
    baseline must never mix items from two different runs for the same account.
    """
    engagement = _engagement_expr()
    reel_views = case((ContentItem.views.isnot(None), cast(ContentItem.views, Float)), else_=None)
    return (
        select(
            ContentItem.run_id.label("run_id"),
            ContentItem.account_id.label("account_id"),
            func.percentile_cont(0.5).within_group(engagement).label("median_engagement"),
            func.percentile_cont(0.5).within_group(reel_views).label("median_views"),
            func.count().label("item_count"),
        )
        .where(item_filter)
        .group_by(ContentItem.run_id, ContentItem.account_id)
        .subquery()
    )


def virality_ratio(
    *,
    likes: int | None,
    comments: int | None,
    views: int | None,
    median_engagement: float | None,
    median_views: float | None,
) -> float | None:
    """Pure function — how hard this item outperformed *that account's own* median within the
    run. Self-relative by design: a meme account and a niche B2B account have wildly different
    normal engagement, so an absolute/global threshold would be meaningless across a competitor
    list. For reels, combines with the views-vs-median-views ratio (max of the two) so a reel
    can register as viral via algorithmic reach or via raw engagement. Returns None when there's
    no usable baseline (e.g. an all-zero-engagement account) — never a fabricated infinite ratio.
    """
    engagement = (likes or 0) + (comments or 0)
    engagement_ratio = engagement / median_engagement if median_engagement else None
    view_ratio = views / median_views if views is not None and median_views else None
    candidates = [r for r in (engagement_ratio, view_ratio) if r is not None]
    return max(candidates) if candidates else None


def virality_ratio_expr(
    median_engagement: ColumnElement[Any],
    median_views: ColumnElement[Any],
    item_count: ColumnElement[Any],
    settings: Settings,
) -> ColumnElement[Any]:
    """SQL mirror of virality_ratio() + bucket_virality()'s min-items guard, so results can be
    sorted by the same "hype index" the badge is based on. Postgres's GREATEST ignores NULL
    arguments (only NULL if every argument is NULL), matching virality_ratio()'s `max` over
    non-null candidates.
    """
    engagement = _engagement_expr()
    engagement_ratio = case(
        (median_engagement.isnot(None) & (median_engagement != 0), engagement / median_engagement),
        else_=None,
    )
    view_ratio = case(
        (
            ContentItem.views.isnot(None) & median_views.isnot(None) & (median_views != 0),
            cast(ContentItem.views, Float) / median_views,
        ),
        else_=None,
    )
    ratio = func.greatest(engagement_ratio, view_ratio)
    return case((item_count < settings.virality_min_items, None), else_=ratio)


def bucket_virality(
    ratio: float | None, item_count: int, settings: Settings
) -> Literal["high", "medium", "low"] | None:
    """Pure function so thresholds and the insufficient-sample guard are unit-testable
    without a database."""
    if item_count < settings.virality_min_items or ratio is None:
        return None
    if ratio >= settings.virality_high_ratio:
        return "high"
    if ratio < settings.virality_low_ratio:
        return "low"
    return "medium"
