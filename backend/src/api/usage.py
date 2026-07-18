from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.db import get_session
from src.models import UsageEvent

router = APIRouter(tags=["usage"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


class KindTotal(BaseModel):
    kind: str
    quantity: int
    cost_usd: Decimal


class UsageOut(BaseModel):
    from_: datetime
    to: datetime
    total_cost_usd: Decimal
    by_kind: list[KindTotal]


@router.get("/me/usage", response_model=UsageOut)
async def get_my_usage(
    user: CurrentUser,
    session: SessionDep,
    from_: datetime = Query(alias="from"),
    to: datetime = Query(),
) -> UsageOut:
    rows = await session.execute(
        select(
            UsageEvent.kind,
            func.sum(UsageEvent.quantity).label("qty"),
            func.sum(UsageEvent.quantity * UsageEvent.unit_cost_usd).label("cost"),
        )
        .where(UsageEvent.user_id == user.id)
        .where(UsageEvent.created_at >= from_)
        .where(UsageEvent.created_at < to)
        .group_by(UsageEvent.kind)
    )
    by_kind = [
        KindTotal(kind=kind, quantity=int(qty or 0), cost_usd=cost or Decimal("0"))
        for kind, qty, cost in rows
    ]
    total_cost_usd = sum((k.cost_usd for k in by_kind), Decimal("0"))
    return UsageOut(from_=from_, to=to, total_cost_usd=total_cost_usd, by_kind=by_kind)
