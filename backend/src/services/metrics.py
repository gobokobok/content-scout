from typing import Any

from sqlalchemy import case, func
from sqlalchemy.sql.elements import ColumnElement

from src.models import ContentItem

# Derived at read time from published_at/now() (per ARCHITECTURE.md) — always fresh, sortable
# server-side, no column to keep in sync. Consumed by the results table query (E5-S1).

MIN_DAYS_DIVISOR = 1.0 / 24  # clamp to 1 hour so a just-published item doesn't divide by ~0


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
