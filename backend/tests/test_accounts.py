import uuid
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tokens import create_access_token
from src.db import get_session
from src.main import app
from tests.conftest import make_project, make_user, make_workspace


class _TestClient(AsyncClient):
    async def __aexit__(self, *exc_info: object) -> None:
        app.dependency_overrides.pop(get_session, None)
        await super().__aexit__(*exc_info)


async def client(session: AsyncSession) -> _TestClient:
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    return _TestClient(transport=transport, base_url="http://test")


def auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


async def _setup_project(session: AsyncSession):
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    await session.commit()
    return owner, project


@patch("src.api.accounts.enqueue_profile_fetch", new_callable=AsyncMock)
async def test_add_and_list_accounts(mock_enqueue: AsyncMock, session: AsyncSession) -> None:
    owner, project = await _setup_project(session)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/accounts",
            json={"entries": ["@one", "https://instagram.com/two/", "not a handle!"]},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["added"]) == 2
        assert {a["handle"] for a in body["added"]} == {"one", "two"}
        assert len(body["errors"]) == 1
        assert body["total"] == 2
        assert mock_enqueue.await_count == 2

        resp = await c.get(f"/projects/{project.id}/accounts", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        assert len(resp.json()) == 2


@patch("src.api.accounts.enqueue_profile_fetch", new_callable=AsyncMock)
async def test_duplicates_deduped_silently(mock_enqueue: AsyncMock, session: AsyncSession) -> None:
    owner, project = await _setup_project(session)

    async with await client(session) as c:
        await c.post(
            f"/projects/{project.id}/accounts",
            json={"entries": ["@dupe"]},
            headers=auth_headers(owner.id),
        )
        resp = await c.post(
            f"/projects/{project.id}/accounts",
            json={"entries": ["@dupe", "https://instagram.com/dupe/", "@dupe"]},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["added"] == []
        assert body["errors"] == []
        assert body["total"] == 1


@patch("src.api.accounts.enqueue_profile_fetch", new_callable=AsyncMock)
async def test_51st_entry_rejected(mock_enqueue: AsyncMock, session: AsyncSession) -> None:
    owner, project = await _setup_project(session)

    async with await client(session) as c:
        first_batch = [f"@acc{i}" for i in range(50)]
        resp = await c.post(
            f"/projects/{project.id}/accounts",
            json={"entries": first_batch},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 201
        assert resp.json()["total"] == 50

        resp = await c.post(
            f"/projects/{project.id}/accounts",
            json={"entries": ["@acc50"]},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["added"] == []
        assert len(body["errors"]) == 1
        assert "50" in body["errors"][0]["message_ru"]
        assert body["total"] == 50


@patch("src.api.accounts.enqueue_profile_fetch", new_callable=AsyncMock)
async def test_remove_account(mock_enqueue: AsyncMock, session: AsyncSession) -> None:
    owner, project = await _setup_project(session)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/accounts",
            json={"entries": ["@removable"]},
            headers=auth_headers(owner.id),
        )
        account_id = resp.json()["added"][0]["id"]

        resp = await c.delete(
            f"/projects/{project.id}/accounts/{account_id}", headers=auth_headers(owner.id)
        )
        assert resp.status_code == 204

        resp = await c.get(f"/projects/{project.id}/accounts", headers=auth_headers(owner.id))
        assert resp.json() == []


async def test_accounts_scoped_to_owning_workspace(session: AsyncSession) -> None:
    owner, project = await _setup_project(session)
    other_user = await make_user(session)
    await make_workspace(session, owner=other_user)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/projects/{project.id}/accounts", headers=auth_headers(other_user.id))
        assert resp.status_code == 404
