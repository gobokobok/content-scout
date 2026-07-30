import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tokens import create_access_token, decode_access_token
from src.main import app
from src.models import Project, Workspace, WorkspaceMember, WorkspaceRole
from tests.conftest import make_user


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
