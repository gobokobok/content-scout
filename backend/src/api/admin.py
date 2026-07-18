import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.db import get_session
from src.models import AnalysisRun, UsageEvent, User
from src.models.usage_event import (
    KIND_APIFY_RESULT,
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
)

router = APIRouter(prefix="/admin", tags=["admin"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]

FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"code": "forbidden", "message_ru": "Доступ запрещён."},
)


class UserUsageRow(BaseModel):
    user_id: uuid.UUID
    email: str
    runs: int
    apify_units: int
    claude_input_tokens: int
    claude_output_tokens: int
    total_cost_usd: Decimal


class AdminUsageOut(BaseModel):
    from_: datetime
    to: datetime
    users: list[UserUsageRow]


@router.get("/usage", response_model=AdminUsageOut)
async def admin_usage(
    current_user: CurrentUser,
    session: SessionDep,
    from_: datetime = Query(alias="from"),
    to: datetime = Query(),
) -> AdminUsageOut:
    if not current_user.is_admin:
        raise FORBIDDEN

    # Per-user usage event aggregation by kind
    usage_rows = await session.execute(
        select(
            UsageEvent.user_id,
            UsageEvent.kind,
            func.sum(UsageEvent.quantity).label("qty"),
            func.sum(UsageEvent.quantity * UsageEvent.unit_cost_usd).label("cost"),
        )
        .where(UsageEvent.created_at >= from_)
        .where(UsageEvent.created_at < to)
        .group_by(UsageEvent.user_id, UsageEvent.kind)
    )

    _empty: dict = {
        "apify_units": 0,
        "claude_input_tokens": 0,
        "claude_output_tokens": 0,
        "total_cost_usd": Decimal("0"),
    }
    user_data: dict[uuid.UUID, dict] = defaultdict(lambda: dict(_empty))
    for user_id, kind, qty, cost in usage_rows:
        d = user_data[user_id]
        d["total_cost_usd"] += cost or Decimal("0")
        if kind == KIND_APIFY_RESULT:
            d["apify_units"] += int(qty or 0)
        elif kind == KIND_CLAUDE_INPUT_TOKENS:
            d["claude_input_tokens"] += int(qty or 0)
        elif kind == KIND_CLAUDE_OUTPUT_TOKENS:
            d["claude_output_tokens"] += int(qty or 0)

    # Per-user run counts in the window
    run_counts_rows = await session.execute(
        select(AnalysisRun.requested_by, func.count(AnalysisRun.id).label("cnt"))
        .where(AnalysisRun.created_at >= from_)
        .where(AnalysisRun.created_at < to)
        .group_by(AnalysisRun.requested_by)
    )
    run_counts: dict[uuid.UUID, int] = {uid: int(cnt) for uid, cnt in run_counts_rows}

    all_user_ids = set(user_data.keys()) | set(run_counts.keys())
    if not all_user_ids:
        return AdminUsageOut(from_=from_, to=to, users=[])

    users_rows = await session.execute(select(User).where(User.id.in_(all_user_ids)))
    users_by_id = {u.id: u for u in users_rows.scalars()}

    result = [
        UserUsageRow(
            user_id=uid,
            email=users_by_id[uid].email if uid in users_by_id else str(uid),
            runs=run_counts.get(uid, 0),
            apify_units=user_data[uid]["apify_units"],
            claude_input_tokens=user_data[uid]["claude_input_tokens"],
            claude_output_tokens=user_data[uid]["claude_output_tokens"],
            total_cost_usd=user_data[uid]["total_cost_usd"],
        )
        for uid in all_user_ids
    ]
    result.sort(key=lambda r: r.total_cost_usd, reverse=True)

    return AdminUsageOut(from_=from_, to=to, users=result)
