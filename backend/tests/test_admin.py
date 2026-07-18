import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tokens import create_access_token
from src.db import get_session
from src.main import app
from src.models import KIND_APIFY_RESULT, KIND_CLAUDE_INPUT_TOKENS, UsageEvent
from tests.conftest import make_project, make_run, make_user, make_workspace


class _TestClient(AsyncClient):
    async def __aexit__(self, *exc_info: object) -> None:
        app.dependency_overrides.pop(get_session, None)
        await super().__aexit__(*exc_info)


async def _client(session: AsyncSession) -> _TestClient:
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    return _TestClient(transport=transport, base_url="http://test")


def auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def _url(from_: datetime, to: datetime) -> str:
    f = from_.isoformat().replace("+", "%2B")
    t = to.isoformat().replace("+", "%2B")
    return f"/admin/usage?from={f}&to={t}"


async def make_admin(session: AsyncSession, **kw):
    user = await make_user(session, **kw)
    user.is_admin = True
    return user


async def test_admin_usage_403_for_non_admin(session: AsyncSession) -> None:
    user = await make_user(session)
    await session.commit()

    now = datetime.now(UTC)
    async with await _client(session) as c:
        resp = await c.get(
            _url(now - timedelta(days=30), now + timedelta(days=1)), headers=auth_headers(user.id)
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "forbidden"


async def test_admin_usage_empty(session: AsyncSession) -> None:
    admin = await make_admin(session)
    await session.commit()

    now = datetime.now(UTC)
    async with await _client(session) as c:
        resp = await c.get(
            _url(now - timedelta(days=30), now + timedelta(days=1)), headers=auth_headers(admin.id)
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["users"] == []


async def test_admin_usage_shows_all_users(session: AsyncSession) -> None:
    admin = await make_admin(session)
    pilot = await make_user(session)
    ws = await make_workspace(session, owner=pilot)
    project = await make_project(session, workspace=ws)
    run = await make_run(session, project=project, requested_by=pilot)
    now = datetime.now(UTC)

    session.add(
        UsageEvent(
            user_id=pilot.id,
            run_id=run.id,
            kind=KIND_APIFY_RESULT,
            quantity=5,
            unit_cost_usd=Decimal("0.00300000"),
            created_at=now - timedelta(days=1),
        )
    )
    await session.commit()

    async with await _client(session) as c:
        resp = await c.get(
            _url(now - timedelta(days=30), now + timedelta(days=1)),
            headers=auth_headers(admin.id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["users"]) == 1
        row = body["users"][0]
        assert row["email"] == pilot.email
        assert row["apify_units"] == 5
        assert row["runs"] == 1


async def test_admin_usage_response_shape(session: AsyncSession) -> None:
    admin = await make_admin(session)
    pilot = await make_user(session)
    now = datetime.now(UTC)

    session.add(
        UsageEvent(
            user_id=pilot.id,
            kind=KIND_CLAUDE_INPUT_TOKENS,
            quantity=100,
            unit_cost_usd=Decimal("0.00000025"),
            created_at=now - timedelta(days=1),
        )
    )
    await session.commit()

    async with await _client(session) as c:
        resp = await c.get(
            _url(now - timedelta(days=30), now + timedelta(days=1)),
            headers=auth_headers(admin.id),
        )
        body = resp.json()
        assert set(body.keys()) == {"from_", "to", "users"}
        row = body["users"][0]
        assert set(row.keys()) == {
            "user_id",
            "email",
            "runs",
            "apify_units",
            "claude_input_tokens",
            "claude_output_tokens",
            "total_cost_usd",
        }
        assert row["claude_input_tokens"] == 100


async def test_me_includes_is_admin(session: AsyncSession) -> None:
    admin = await make_admin(session)
    regular = await make_user(session)
    await session.commit()

    async with await _client(session) as c:
        resp = await c.get("/auth/me", headers=auth_headers(admin.id))
        assert resp.json()["is_admin"] is True

        resp2 = await c.get("/auth/me", headers=auth_headers(regular.id))
        assert resp2.json()["is_admin"] is False
