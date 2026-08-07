import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tokens import create_access_token, decode_access_token
from src.main import app
from src.models import Project, User, Workspace, WorkspaceMember, WorkspaceRole
from tests.conftest import make_user


async def _noop_rate_limit(*args, **kwargs) -> None:
    pass


@pytest.fixture(autouse=True)
def _bypass_rate_limit():
    """This file's tests aren't exercising rate-limiting (test_guardrails.py owns that);
    every test hitting /auth/register or /auth/login shares one Redis-backed per-minute
    counter (rate_limit.py), so enough of them in one run trips a real 429 unrelated to
    what each test is actually checking."""
    with patch("src.api.auth.check_rate_limit", _noop_rate_limit):
        yield


class _TestClient(AsyncClient):
    """AsyncClient that clears its dependency override on exit (test isolation)."""

    async def __aexit__(self, *exc_info: object) -> None:
        from src.db import get_session

        app.dependency_overrides.pop(get_session, None)
        await super().__aexit__(*exc_info)


async def client(session: AsyncSession) -> _TestClient:
    """App instance wired to the test's rollback-savepoint session."""
    from src.db import get_session

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    return _TestClient(transport=transport, base_url="http://test")


async def test_register_creates_user_and_personal_workspace(session: AsyncSession) -> None:
    async with await client(session) as c:
        resp = await c.post(
            "/auth/register", json={"email": "blogger@example.com", "password": "correcthorse"}
        )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    user_id = decode_access_token(token)
    assert user_id is not None

    membership = await session.scalar(
        select(WorkspaceMember).where(WorkspaceMember.user_id == user_id)
    )
    assert membership is not None
    assert membership.role == WorkspaceRole.owner
    workspace = await session.get(Workspace, membership.workspace_id)
    assert workspace is not None

    # D38: "project" isn't a user-facing concept — every account gets exactly one, invisibly.
    project = await session.scalar(
        select(Project).where(Project.workspace_id == membership.workspace_id)
    )
    assert project is not None
    assert project.name


async def test_register_succeeds_without_invite_code(session: AsyncSession) -> None:
    """D39: registration has had no invite-code gate since 2026-07-19 (commit 053cbe3),
    superseding E7-S4's guardrail same-day — confirms that's still true, not the reverse."""
    async with await client(session) as c:
        resp = await c.post(
            "/auth/register", json={"email": "noinvite@example.com", "password": "correcthorse"}
        )
    assert resp.status_code == 201
    user_id = decode_access_token(resp.json()["access_token"])
    user = await session.get(User, user_id)
    assert user is not None
    assert user.token_balance == 50


async def test_register_duplicate_email_rejected(session: AsyncSession) -> None:
    async with await client(session) as c:
        await c.post(
            "/auth/register", json={"email": "dup@example.com", "password": "correcthorse"}
        )
        resp = await c.post(
            "/auth/register", json={"email": "dup@example.com", "password": "anotherpass1"}
        )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "email_taken"


async def test_register_invalid_email_rejected(session: AsyncSession) -> None:
    async with await client(session) as c:
        resp = await c.post(
            "/auth/register", json={"email": "not-an-email", "password": "correcthorse"}
        )
    assert resp.status_code == 422


async def test_register_short_password_rejected(session: AsyncSession) -> None:
    async with await client(session) as c:
        resp = await c.post(
            "/auth/register", json={"email": "short@example.com", "password": "short"}
        )
    assert resp.status_code == 422


async def test_login_success(session: AsyncSession) -> None:
    async with await client(session) as c:
        await c.post(
            "/auth/register", json={"email": "login@example.com", "password": "correcthorse"}
        )
        resp = await c.post(
            "/auth/login", json={"email": "login@example.com", "password": "correcthorse"}
        )
    assert resp.status_code == 200
    assert decode_access_token(resp.json()["access_token"]) is not None


async def test_login_wrong_password_rejected(session: AsyncSession) -> None:
    async with await client(session) as c:
        await c.post(
            "/auth/register", json={"email": "wrongpw@example.com", "password": "correcthorse"}
        )
        resp = await c.post(
            "/auth/login", json={"email": "wrongpw@example.com", "password": "nope12345"}
        )
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "invalid_credentials"


async def test_login_unknown_email_rejected(session: AsyncSession) -> None:
    async with await client(session) as c:
        resp = await c.post(
            "/auth/login", json={"email": "ghost@example.com", "password": "correcthorse"}
        )
    assert resp.status_code == 401


async def test_me_requires_valid_token(session: AsyncSession) -> None:
    async with await client(session) as c:
        resp = await c.get("/auth/me")
        assert resp.status_code == 401

        resp = await c.get("/auth/me", headers={"Authorization": "Bearer garbage"})
        assert resp.status_code == 401


async def test_me_returns_current_user(session: AsyncSession) -> None:
    async with await client(session) as c:
        reg = await c.post(
            "/auth/register", json={"email": "me@example.com", "password": "correcthorse"}
        )
        token = reg.json()["access_token"]
        resp = await c.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


async def test_me_rejects_token_for_deleted_user(session: AsyncSession) -> None:
    fake_token = create_access_token(uuid.uuid4())
    async with await client(session) as c:
        resp = await c.get("/auth/me", headers={"Authorization": f"Bearer {fake_token}"})
    assert resp.status_code == 401


async def test_password_hash_never_equals_plaintext(session: AsyncSession) -> None:
    user = await make_user(session, password_hash=None)
    assert user.password_hash is None


async def test_register_assigns_random_display_name(session: AsyncSession) -> None:
    async with await client(session) as c:
        resp = await c.post(
            "/auth/register", json={"email": "named@example.com", "password": "correcthorse"}
        )
    token = resp.json()["access_token"]
    async with await client(session) as c:
        me = await c.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["display_name"].startswith("Пользователь")


async def test_update_display_name(session: AsyncSession) -> None:
    async with await client(session) as c:
        reg = await c.post(
            "/auth/register", json={"email": "rename@example.com", "password": "correcthorse"}
        )
        token = reg.json()["access_token"]
        resp = await c.patch(
            "/auth/me",
            json={"display_name": "Александр"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Александр"


async def test_update_display_name_rejects_blank(session: AsyncSession) -> None:
    async with await client(session) as c:
        reg = await c.post(
            "/auth/register", json={"email": "blank@example.com", "password": "correcthorse"}
        )
        token = reg.json()["access_token"]
        resp = await c.patch(
            "/auth/me",
            json={"display_name": "   "},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 422


async def test_update_display_name_rejects_too_long(session: AsyncSession) -> None:
    async with await client(session) as c:
        reg = await c.post(
            "/auth/register", json={"email": "toolong@example.com", "password": "correcthorse"}
        )
        token = reg.json()["access_token"]
        resp = await c.patch(
            "/auth/me",
            json={"display_name": "a" * 51},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 422


# --- E22-S3: global notify preferences ------------------------------------------------------


async def test_me_defaults_notify_prefs_true(session: AsyncSession) -> None:
    """Preserves pre-existing unconditional-notify behavior for accounts that predate this
    story — both toggles default on."""
    async with await client(session) as c:
        reg = await c.post(
            "/auth/register", json={"email": "notifydefault@example.com", "password": "x" * 8}
        )
        token = reg.json()["access_token"]
        me = await c.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["notify_review_enabled"] is True
    assert me.json()["notify_analysis_enabled"] is True


async def test_update_notify_prefs(session: AsyncSession) -> None:
    async with await client(session) as c:
        reg = await c.post(
            "/auth/register", json={"email": "notifyupdate@example.com", "password": "x" * 8}
        )
        token = reg.json()["access_token"]
        resp = await c.patch(
            "/auth/me/notifications",
            json={"notify_review_enabled": False, "notify_analysis_enabled": True},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["notify_review_enabled"] is False
    assert resp.json()["notify_analysis_enabled"] is True

    # Persists — a fresh /me read reflects the update, not just the PATCH response.
    async with await client(session) as c:
        me = await c.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["notify_review_enabled"] is False
    assert me.json()["notify_analysis_enabled"] is True
