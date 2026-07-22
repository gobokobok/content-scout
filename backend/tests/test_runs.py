import uuid
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tokens import create_access_token
from src.db import get_session
from src.main import app
from src.models import RunStatus, RunSummaryStatus
from tests.conftest import (
    make_account,
    make_account_list,
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


async def _setup_project_with_accounts(session: AsyncSession, n: int = 3):
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    account_list = await make_account_list(session, project=project)
    for _ in range(n):
        await make_account(session, account_list=account_list)
    await session.commit()
    return owner, project


async def test_estimate_reflects_account_count_and_duration(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=4)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/runs/estimate",
            json={"duration_days": 3},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["accounts_count"] == 4
        assert body["apify_units"] > 0
        assert float(body["estimated_cost_usd"]) > 0


async def test_estimate_with_item_limit(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=4)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/runs/estimate",
            json={"item_limit": 10},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["apify_units"] == 40  # 4 accounts * 10 items


async def test_run_request_rejects_both_duration_and_item_limit(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=1)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/runs/estimate",
            json={"duration_days": 3, "item_limit": 10},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 422


async def test_run_request_rejects_neither_duration_nor_item_limit(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=1)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/runs/estimate",
            json={},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 422


async def test_duration_out_of_range_rejected(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=1)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/runs/estimate",
            json={"duration_days": 8},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 422


@patch("src.api.runs.enqueue_run", new_callable=AsyncMock)
async def test_create_run_enqueues_job(mock_enqueue: AsyncMock, session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=2)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/runs",
            json={"duration_days": 5},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == RunStatus.pending.value
        assert body["duration_days"] == 5
        assert body["progress_summarized"] == 0
        assert body["total_input_tokens"] == 0
        assert body["total_output_tokens"] == 0

    mock_enqueue.assert_awaited_once()


@patch("src.api.runs.enqueue_run", new_callable=AsyncMock)
async def test_create_run_with_item_limit(mock_enqueue: AsyncMock, session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=2)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/runs",
            json={"item_limit": 15},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["item_limit"] == 15
        assert body["duration_days"] is None

    mock_enqueue.assert_awaited_once()


@patch("src.api.runs.enqueue_run", new_callable=AsyncMock)
async def test_create_run_with_no_accounts_rejected(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    await session.commit()

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/runs",
            json={"duration_days": 3},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "no_accounts_to_analyze"

    mock_enqueue.assert_not_awaited()


async def test_get_run_scoped_to_owning_workspace(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=1)
    run = await make_run(session, project=project, requested_by=owner)

    other_user = await make_user(session)
    await make_workspace(session, owner=other_user)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/runs/{run.id}", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        assert resp.json()["id"] == str(run.id)

        resp = await c.get(f"/runs/{run.id}", headers=auth_headers(other_user.id))
        assert resp.status_code == 404


async def test_get_run_includes_summary_fields(session: AsyncSession) -> None:
    """E15-S3: the run detail page's Summary tab reads these straight off RunOut."""
    owner, project = await _setup_project_with_accounts(session, n=1)
    run = await make_run(session, project=project, requested_by=owner)
    run.summary_status = RunSummaryStatus.done
    run.summary_text = "Конкуренты публикуют в основном ролики про путешествия."
    run.summary_topics = ["Путешествия", "Еда"]
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/runs/{run.id}", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        body = resp.json()
        assert body["summary_status"] == "done"
        assert body["summary_text"] == "Конкуренты публикуют в основном ролики про путешествия."
        assert body["summary_topics"] == ["Путешествия", "Еда"]


async def test_get_run_default_summary_status_is_pending(session: AsyncSession) -> None:
    """Runs created before E15-S1 (or before summary generation runs) default to pending."""
    owner, project = await _setup_project_with_accounts(session, n=1)
    run = await make_run(session, project=project, requested_by=owner)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/runs/{run.id}", headers=auth_headers(owner.id))
        body = resp.json()
        assert body["summary_status"] == "pending"
        assert body["summary_text"] is None
        assert body["summary_topics"] is None
