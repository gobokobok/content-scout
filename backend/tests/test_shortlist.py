import uuid
from datetime import UTC, datetime, timedelta

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tokens import create_access_token
from src.db import get_session
from src.main import app
from src.models import ContentType
from tests.conftest import (
    make_account,
    make_account_list,
    make_content_item,
    make_project,
    make_run,
    make_user,
    make_workspace,
)


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


async def _setup(session: AsyncSession):
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list, handle="natgeo")
    run = await make_run(session, project=project, requested_by=owner)
    now = datetime.now(UTC)
    item1 = await make_content_item(
        session,
        run=run,
        account=account,
        type=ContentType.reel,
        published_at=now - timedelta(days=2),
        views=1000,
        likes=100,
    )
    item2 = await make_content_item(
        session,
        run=run,
        account=account,
        type=ContentType.post,
        published_at=now - timedelta(days=1),
        views=None,
        likes=50,
    )
    await session.commit()
    return owner, project, run, item1, item2


async def test_add_to_shortlist_and_list(session: AsyncSession) -> None:
    owner, project, run, item1, item2 = await _setup(session)

    async with await client(session) as c:
        headers = auth_headers(owner.id)

        # Add two items
        resp = await c.post(
            f"/projects/{project.id}/shortlist/items",
            headers=headers,
            json={"item_ids": [str(item1.id), str(item2.id)]},
        )
        assert resp.status_code == 204

        # List shortlist
        resp = await c.get(f"/projects/{project.id}/shortlist/items", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        ids = {entry["content_item_id"] for entry in body}
        assert str(item1.id) in ids and str(item2.id) in ids


async def test_add_is_idempotent(session: AsyncSession) -> None:
    owner, project, run, item1, _ = await _setup(session)

    async with await client(session) as c:
        headers = auth_headers(owner.id)
        for _ in range(3):
            resp = await c.post(
                f"/projects/{project.id}/shortlist/items",
                headers=headers,
                json={"item_ids": [str(item1.id)]},
            )
            assert resp.status_code == 204

        resp = await c.get(f"/projects/{project.id}/shortlist/items", headers=headers)
        assert len(resp.json()) == 1


async def test_remove_from_shortlist(session: AsyncSession) -> None:
    owner, project, run, item1, _ = await _setup(session)

    async with await client(session) as c:
        headers = auth_headers(owner.id)

        await c.post(
            f"/projects/{project.id}/shortlist/items",
            headers=headers,
            json={"item_ids": [str(item1.id)]},
        )

        resp = await c.delete(f"/projects/{project.id}/shortlist/items/{item1.id}", headers=headers)
        assert resp.status_code == 204

        resp = await c.get(f"/projects/{project.id}/shortlist/items", headers=headers)
        assert len(resp.json()) == 0


async def test_remove_then_re_add(session: AsyncSession) -> None:
    owner, project, run, item1, _ = await _setup(session)

    async with await client(session) as c:
        headers = auth_headers(owner.id)

        await c.post(
            f"/projects/{project.id}/shortlist/items",
            headers=headers,
            json={"item_ids": [str(item1.id)]},
        )
        await c.delete(f"/projects/{project.id}/shortlist/items/{item1.id}", headers=headers)
        # Re-add
        resp = await c.post(
            f"/projects/{project.id}/shortlist/items",
            headers=headers,
            json={"item_ids": [str(item1.id)]},
        )
        assert resp.status_code == 204

        resp = await c.get(f"/projects/{project.id}/shortlist/items", headers=headers)
        assert len(resp.json()) == 1


async def test_items_endpoint_returns_in_shortlist(session: AsyncSession) -> None:
    owner, project, run, item1, item2 = await _setup(session)

    async with await client(session) as c:
        headers = auth_headers(owner.id)

        # Before adding: in_shortlist should be False
        resp = await c.get(f"/runs/{run.id}/items", headers=headers)
        body = resp.json()
        assert all(not it["in_shortlist"] for it in body["items"])

        # Add item1
        await c.post(
            f"/projects/{project.id}/shortlist/items",
            headers=headers,
            json={"item_ids": [str(item1.id)]},
        )

        resp = await c.get(f"/runs/{run.id}/items", headers=headers)
        by_id = {it["id"]: it for it in resp.json()["items"]}
        assert by_id[str(item1.id)]["in_shortlist"] is True
        assert by_id[str(item2.id)]["in_shortlist"] is False


async def test_shortlist_404_for_wrong_user(session: AsyncSession) -> None:
    owner, project, run, item1, _ = await _setup(session)
    other = await make_user(session)
    await make_workspace(session, owner=other)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(
            f"/projects/{project.id}/shortlist/items",
            headers=auth_headers(other.id),
        )
        assert resp.status_code == 404
