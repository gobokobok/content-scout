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


async def _setup_run_with_items(session: AsyncSession):
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    account_list = await make_account_list(session, project=project)
    account_a = await make_account(session, account_list=account_list, handle="natgeo")
    account_b = await make_account(session, account_list=account_list, handle="therock")
    run = await make_run(session, project=project, requested_by=owner)

    now = datetime.now(UTC)
    await make_content_item(
        session,
        run=run,
        account=account_a,
        type=ContentType.reel,
        published_at=now - timedelta(days=2),
        views=1000,
        likes=100,
        title="Reel A",
    )
    await make_content_item(
        session,
        run=run,
        account=account_b,
        type=ContentType.post,
        published_at=now - timedelta(days=1),
        views=None,
        likes=50,
        title="Post B",
    )
    await make_content_item(
        session,
        run=run,
        account=account_a,
        type=ContentType.carousel,
        published_at=now - timedelta(days=4),
        views=None,
        likes=200,
        title="Carousel C",
    )
    await session.commit()
    return owner, run


async def test_list_items_default_sort_and_shape(session: AsyncSession) -> None:
    owner, run = await _setup_run_with_items(session)

    async with await client(session) as c:
        resp = await c.get(f"/runs/{run.id}/items", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert body["page"] == 1
        assert body["page_size"] == 50
        assert len(body["items"]) == 3

        first = body["items"][0]
        assert set(first.keys()) == {
            "id",
            "account_handle",
            "followers_count",
            "published_at",
            "type",
            "title",
            "url",
            "summary",
            "likes",
            "views",
            "days_since_published",
            "views_per_day",
            "likes_per_day",
            "in_shortlist",
        }


async def test_views_null_sorts_last_regardless_of_direction(session: AsyncSession) -> None:
    owner, run = await _setup_run_with_items(session)

    async with await client(session) as c:
        resp = await c.get(
            f"/runs/{run.id}/items?sort=views&order=desc", headers=auth_headers(owner.id)
        )
        titles = [item["title"] for item in resp.json()["items"]]
        assert titles[0] == "Reel A"
        assert titles[-2:] == ["Post B", "Carousel C"] or titles[-2:] == ["Carousel C", "Post B"]

        resp = await c.get(
            f"/runs/{run.id}/items?sort=views&order=asc", headers=auth_headers(owner.id)
        )
        titles = [item["title"] for item in resp.json()["items"]]
        assert titles[-1] in ("Post B", "Carousel C")
        # only one non-null views value, so it must be first in ascending order too
        assert titles[0] == "Reel A"


async def test_sort_by_likes_ascending(session: AsyncSession) -> None:
    owner, run = await _setup_run_with_items(session)

    async with await client(session) as c:
        resp = await c.get(
            f"/runs/{run.id}/items?sort=likes&order=asc", headers=auth_headers(owner.id)
        )
        likes = [item["likes"] for item in resp.json()["items"]]
        assert likes == sorted(likes)


async def test_post_and_carousel_views_are_null_not_zero(session: AsyncSession) -> None:
    owner, run = await _setup_run_with_items(session)

    async with await client(session) as c:
        resp = await c.get(f"/runs/{run.id}/items", headers=auth_headers(owner.id))
        by_title = {item["title"]: item for item in resp.json()["items"]}
        assert by_title["Post B"]["views"] is None
        assert by_title["Carousel C"]["views"] is None
        assert by_title["Post B"]["views_per_day"] is None
        assert by_title["Reel A"]["views"] == 1000
        assert by_title["Reel A"]["views_per_day"] is not None


async def test_items_scoped_to_owning_workspace(session: AsyncSession) -> None:
    owner, run = await _setup_run_with_items(session)
    other_user = await make_user(session)
    await make_workspace(session, owner=other_user)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/runs/{run.id}/items", headers=auth_headers(other_user.id))
        assert resp.status_code == 404


async def test_list_runs_for_project(session: AsyncSession) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    run_1 = await make_run(session, project=project, requested_by=owner)
    run_2 = await make_run(session, project=project, requested_by=owner)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/projects/{project.id}/runs", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()]
        assert set(ids) == {str(run_1.id), str(run_2.id)}
