import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tokens import create_access_token
from src.db import get_session
from src.main import app
from tests.conftest import make_project, make_run, make_user, make_workspace


class _TestClient(AsyncClient):
    """AsyncClient that clears its dependency override on exit (test isolation)."""

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


async def test_create_and_list_project(session: AsyncSession) -> None:
    user = await make_user(session)
    await make_workspace(session, owner=user)
    await session.commit()

    async with await client(session) as c:
        resp = await c.post("/projects", json={"name": "Мой проект"}, headers=auth_headers(user.id))
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Мой проект"
        assert body["archived_at"] is None

        resp = await c.get("/projects", headers=auth_headers(user.id))
        assert resp.status_code == 200
        assert [p["name"] for p in resp.json()] == ["Мой проект"]


async def test_get_project_scoped_to_workspace(session: AsyncSession) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)

    other_user = await make_user(session)
    await make_workspace(session, owner=other_user)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/projects/{project.id}", headers=auth_headers(owner.id))
        assert resp.status_code == 200

        resp = await c.get(f"/projects/{project.id}", headers=auth_headers(other_user.id))
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "project_not_found"


async def test_rename_project(session: AsyncSession) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws, name="Старое имя")
    await session.commit()

    async with await client(session) as c:
        resp = await c.patch(
            f"/projects/{project.id}", json={"name": "Новое имя"}, headers=auth_headers(owner.id)
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Новое имя"


async def test_archive_project_hidden_from_default_list(session: AsyncSession) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    await session.commit()

    async with await client(session) as c:
        resp = await c.post(f"/projects/{project.id}/archive", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        assert resp.json()["archived_at"] is not None

        resp = await c.get("/projects", headers=auth_headers(owner.id))
        assert resp.json() == []

        resp = await c.get("/projects?include_archived=true", headers=auth_headers(owner.id))
        assert len(resp.json()) == 1


async def test_unauthenticated_rejected(session: AsyncSession) -> None:
    async with await client(session) as c:
        resp = await c.get("/projects")
        assert resp.status_code == 401


async def test_project_stats_sums_items_across_runs(session: AsyncSession) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    await make_run(session, project=project, requested_by=owner, progress_items=4)
    await make_run(session, project=project, requested_by=owner, progress_items=6)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/projects/{project.id}/stats", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        assert resp.json() == {"lifetime_items_analyzed": 10}


async def test_project_stats_zero_with_no_runs(session: AsyncSession) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/projects/{project.id}/stats", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        assert resp.json() == {"lifetime_items_analyzed": 0}


async def test_project_stats_scoped_to_workspace(session: AsyncSession) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    await session.commit()

    other_user = await make_user(session)
    await make_workspace(session, owner=other_user)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/projects/{project.id}/stats", headers=auth_headers(other_user.id))
        assert resp.status_code == 404
