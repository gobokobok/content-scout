import uuid
from datetime import UTC, datetime, timedelta

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tokens import create_access_token
from src.db import get_session
from src.main import app
from src.models import ContentType, RunStatus
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
        comments=10,
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
        comments=30,
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
        comments=20,
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
            "comments",
            "days_since_published",
            "views_per_day",
            "likes_per_day",
            "engagement_rate",
            "virality",
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


async def test_sort_by_comments_and_value_present(session: AsyncSession) -> None:
    owner, run = await _setup_run_with_items(session)

    async with await client(session) as c:
        resp = await c.get(
            f"/runs/{run.id}/items?sort=comments&order=desc", headers=auth_headers(owner.id)
        )
        comments = [item["comments"] for item in resp.json()["items"]]
        assert comments == [30, 20, 10]


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


async def test_virality_badge_and_engagement_rate(session: AsyncSession) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    account_list = await make_account_list(session, project=project)
    # 4 items, 3 at a baseline engagement (median 100) + one clear outlier (5x median) — enough
    # items to clear the default virality_min_items=3 guard and land the outlier in "high".
    viral_account = await make_account(
        session, account_list=account_list, handle="viral", followers_count=1000
    )
    # Only 2 items — below virality_min_items=3, so this account must get no badge at all.
    quiet_account = await make_account(session, account_list=account_list, handle="quiet")
    run = await make_run(session, project=project, requested_by=owner)

    now = datetime.now(UTC)
    for i in range(3):
        await make_content_item(
            session,
            run=run,
            account=viral_account,
            type=ContentType.post,
            published_at=now - timedelta(days=1),
            likes=100,
            comments=0,
            views=None,
            title=f"Baseline {i}",
        )
    await make_content_item(
        session,
        run=run,
        account=viral_account,
        type=ContentType.post,
        published_at=now - timedelta(days=1),
        likes=500,
        comments=0,
        views=None,
        title="Outlier",
    )
    for i in range(2):
        await make_content_item(
            session,
            run=run,
            account=quiet_account,
            type=ContentType.post,
            published_at=now - timedelta(days=1),
            likes=10,
            comments=0,
            views=None,
            title=f"Quiet {i}",
        )
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/runs/{run.id}/items", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        by_title = {item["title"]: item for item in resp.json()["items"]}

        assert by_title["Outlier"]["virality"] == "high"
        assert by_title["Outlier"]["engagement_rate"] == 500 / 1000
        assert by_title["Baseline 0"]["virality"] == "medium"

        assert by_title["Quiet 0"]["virality"] is None


async def test_sort_by_virality(session: AsyncSession) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    account_list = await make_account_list(session, project=project)
    viral_account = await make_account(
        session, account_list=account_list, handle="viral", followers_count=1000
    )
    # Below virality_min_items=3 — its ratio must sort last regardless of direction.
    quiet_account = await make_account(session, account_list=account_list, handle="quiet")
    run = await make_run(session, project=project, requested_by=owner)

    now = datetime.now(UTC)
    for i in range(3):
        await make_content_item(
            session,
            run=run,
            account=viral_account,
            type=ContentType.post,
            published_at=now - timedelta(days=1),
            likes=100,
            comments=0,
            views=None,
            title=f"Baseline {i}",
        )
    await make_content_item(
        session,
        run=run,
        account=viral_account,
        type=ContentType.post,
        published_at=now - timedelta(days=1),
        likes=500,
        comments=0,
        views=None,
        title="Outlier",
    )
    for i in range(2):
        await make_content_item(
            session,
            run=run,
            account=quiet_account,
            type=ContentType.post,
            published_at=now - timedelta(days=1),
            likes=10,
            comments=0,
            views=None,
            title=f"Quiet {i}",
        )
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(
            f"/runs/{run.id}/items?sort=virality&order=desc", headers=auth_headers(owner.id)
        )
        titles = [item["title"] for item in resp.json()["items"]]
        assert titles[0] == "Outlier"
        assert set(titles[-2:]) == {"Quiet 0", "Quiet 1"}

        resp = await c.get(
            f"/runs/{run.id}/items?sort=virality&order=asc", headers=auth_headers(owner.id)
        )
        titles = [item["title"] for item in resp.json()["items"]]
        # nulls sort last regardless of direction; Outlier has the highest ratio, so it's last
        # among the non-null items (right before the null/Quiet block) in ascending order.
        assert set(titles[-2:]) == {"Quiet 0", "Quiet 1"}
        assert titles[-3] == "Outlier"


async def test_top_virality_excludes_insufficient_sample_and_orders_desc(
    session: AsyncSession,
) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    account_list = await make_account_list(session, project=project)
    viral_account = await make_account(
        session, account_list=account_list, handle="viral", followers_count=1000
    )
    # Below virality_min_items=3 — must be excluded entirely, not just sorted last.
    quiet_account = await make_account(session, account_list=account_list, handle="quiet")
    run = await make_run(session, project=project, requested_by=owner)

    now = datetime.now(UTC)
    for i in range(3):
        await make_content_item(
            session,
            run=run,
            account=viral_account,
            type=ContentType.post,
            published_at=now - timedelta(days=1),
            likes=100,
            comments=0,
            views=None,
            title=f"Baseline {i}",
        )
    await make_content_item(
        session,
        run=run,
        account=viral_account,
        type=ContentType.post,
        published_at=now - timedelta(days=1),
        likes=500,
        comments=0,
        views=None,
        title="Outlier",
    )
    for i in range(2):
        await make_content_item(
            session,
            run=run,
            account=quiet_account,
            type=ContentType.post,
            published_at=now - timedelta(days=1),
            likes=10,
            comments=0,
            views=None,
            title=f"Quiet {i}",
        )
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/runs/{run.id}/top-virality", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        titles = [item["title"] for item in resp.json()["items"]]

        assert titles[0] == "Outlier"
        assert "Quiet 0" not in titles
        assert "Quiet 1" not in titles
        assert len(titles) == 4  # 3 baseline + 1 outlier; quiet account excluded


async def test_top_virality_respects_limit(session: AsyncSession) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list, handle="prolific")
    run = await make_run(session, project=project, requested_by=owner)

    now = datetime.now(UTC)
    # 6 qualifying items (>= virality_min_items=3), each with a distinct engagement so
    # the ratio ordering is unambiguous.
    for i in range(6):
        await make_content_item(
            session,
            run=run,
            account=account,
            type=ContentType.post,
            published_at=now - timedelta(days=1),
            likes=10 * (i + 1),
            comments=0,
            views=None,
            title=f"Item {i}",
        )
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/runs/{run.id}/top-virality", headers=auth_headers(owner.id))
        assert len(resp.json()["items"]) == 5  # default limit

        resp = await c.get(f"/runs/{run.id}/top-virality?limit=2", headers=auth_headers(owner.id))
        titles = [item["title"] for item in resp.json()["items"]]
        assert titles == ["Item 5", "Item 4"]


async def test_top_virality_scoped_to_owning_workspace(session: AsyncSession) -> None:
    owner, run = await _setup_run_with_items(session)
    other_user = await make_user(session)
    await make_workspace(session, owner=other_user)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/runs/{run.id}/top-virality", headers=auth_headers(other_user.id))
        assert resp.status_code == 404


async def test_items_scoped_to_owning_workspace(session: AsyncSession) -> None:
    owner, run = await _setup_run_with_items(session)
    other_user = await make_user(session)
    await make_workspace(session, owner=other_user)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/runs/{run.id}/items", headers=auth_headers(other_user.id))
        assert resp.status_code == 404


async def test_project_items_all_runs_pools_across_runs(session: AsyncSession) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list, handle="natgeo")
    run_1 = await make_run(session, project=project, requested_by=owner, status=RunStatus.done)
    run_2 = await make_run(session, project=project, requested_by=owner, status=RunStatus.done)

    await make_content_item(session, run=run_1, account=account, title="From run 1")
    await make_content_item(session, run=run_2, account=account, title="From run 2")
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/projects/{project.id}/items", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        titles = {item["title"] for item in body["items"]}
        assert titles == {"From run 1", "From run 2"}


async def test_project_items_filters_by_run_id(session: AsyncSession) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list, handle="natgeo")
    run_1 = await make_run(session, project=project, requested_by=owner, status=RunStatus.done)
    run_2 = await make_run(session, project=project, requested_by=owner, status=RunStatus.done)

    await make_content_item(session, run=run_1, account=account, title="From run 1")
    await make_content_item(session, run=run_2, account=account, title="From run 2")
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(
            f"/projects/{project.id}/items?run_id={run_1.id}", headers=auth_headers(owner.id)
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "From run 1"


async def test_project_items_excludes_non_done_runs(session: AsyncSession) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list, handle="natgeo")
    done_run = await make_run(session, project=project, requested_by=owner, status=RunStatus.done)
    pending_run = await make_run(
        session, project=project, requested_by=owner, status=RunStatus.pending
    )

    await make_content_item(session, run=done_run, account=account, title="Done item")
    await make_content_item(session, run=pending_run, account=account, title="Pending item")
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/projects/{project.id}/items", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        titles = {item["title"] for item in resp.json()["items"]}
        assert titles == {"Done item"}


async def test_project_items_starred_only_filter(session: AsyncSession) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list, handle="natgeo")
    run = await make_run(session, project=project, requested_by=owner, status=RunStatus.done)

    starred = await make_content_item(session, run=run, account=account, title="Starred")
    await make_content_item(session, run=run, account=account, title="Not starred")
    await session.commit()

    async with await client(session) as c:
        headers = auth_headers(owner.id)
        await c.post(
            f"/projects/{project.id}/shortlist/items",
            json={"item_ids": [str(starred.id)]},
            headers=headers,
        )

        resp = await c.get(f"/projects/{project.id}/items?starred_only=true", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "Starred"
        assert body["items"][0]["in_shortlist"] is True


async def test_project_items_scoped_to_owning_workspace(session: AsyncSession) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    other_user = await make_user(session)
    await make_workspace(session, owner=other_user)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/projects/{project.id}/items", headers=auth_headers(other_user.id))
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
