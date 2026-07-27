import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tokens import create_access_token
from src.db import get_session
from src.main import app
from src.models import (
    ContentItem,
    DeepAnalysisItem,
    DeepAnalysisItemStatus,
    DeepAnalysisStatus,
    RunStatus,
)
from tests.conftest import (
    make_content_item,
    make_deep_analysis,
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


async def _setup_done_run(session: AsyncSession, *, token_balance: int = 1000):
    owner = await make_user(session, token_balance=token_balance)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    run = await make_run(session, project=project, requested_by=owner)
    run.status = RunStatus.done
    await make_content_item(session, run=run)
    await make_content_item(session, run=run)
    await session.commit()
    return owner, project, run


async def test_estimate_deep_analysis_matches_actual_charge(session: AsyncSession) -> None:
    owner, project, run = await _setup_done_run(session, token_balance=1000)

    async with await client(session) as c:
        estimate = await c.get(
            f"/projects/{project.id}/runs/{run.id}/deep-analyses/estimate",
            headers=auth_headers(owner.id),
        )
        assert estimate.status_code == 200
        estimated_tokens = estimate.json()["tokens"]
        assert estimated_tokens > 0

        with patch("src.api.deep_analyses.enqueue_deep_analysis", new_callable=AsyncMock):
            created = await c.post(
                f"/projects/{project.id}/runs/{run.id}/deep-analyses",
                headers=auth_headers(owner.id),
            )
        assert created.json()["tokens_charged"] == estimated_tokens


@patch("src.api.deep_analyses.enqueue_deep_analysis", new_callable=AsyncMock)
async def test_create_deep_analysis_deducts_tokens_and_enqueues(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project, run = await _setup_done_run(session, token_balance=1000)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/runs/{run.id}/deep-analyses",
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == DeepAnalysisStatus.pending.value
        assert body["tokens_charged"] > 0
        assert body["run_id"] == str(run.id)
        assert body["project_id"] == str(project.id)

        me = await c.get("/auth/me", headers=auth_headers(owner.id))
        assert me.json()["token_balance"] == 1000 - body["tokens_charged"]

    mock_enqueue.assert_awaited_once()


@patch("src.api.deep_analyses.enqueue_deep_analysis", new_callable=AsyncMock)
async def test_create_deep_analysis_rejects_run_not_done(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner = await make_user(session, token_balance=1000)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    run = await make_run(session, project=project, requested_by=owner)  # default status: pending
    await session.commit()

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/runs/{run.id}/deep-analyses",
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "run_not_done"

    mock_enqueue.assert_not_awaited()


@patch("src.api.deep_analyses.enqueue_deep_analysis", new_callable=AsyncMock)
async def test_create_deep_analysis_rejects_insufficient_balance(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project, run = await _setup_done_run(session, token_balance=0)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/runs/{run.id}/deep-analyses",
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 402
        assert resp.json()["detail"]["code"] == "insufficient_token_balance"

    mock_enqueue.assert_not_awaited()


async def test_create_deep_analysis_404_for_foreign_run(session: AsyncSession) -> None:
    owner, project, run = await _setup_done_run(session)
    other_owner = await make_user(session)
    other_ws = await make_workspace(session, owner=other_owner)
    other_project = await make_project(session, workspace=other_ws)
    await session.commit()

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{other_project.id}/runs/{run.id}/deep-analyses",
            headers=auth_headers(other_owner.id),
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "run_not_found"


async def test_list_deep_analyses_orders_most_recent_first(session: AsyncSession) -> None:
    owner, project, run = await _setup_done_run(session)
    now = datetime.now(UTC)
    first = await make_deep_analysis(
        session, run=run, requested_by=owner, created_at=now - timedelta(minutes=5)
    )
    second = await make_deep_analysis(session, run=run, requested_by=owner, created_at=now)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/projects/{project.id}/deep-analyses", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        ids = [row["id"] for row in resp.json()]
        assert ids == [str(second.id), str(first.id)]


async def test_get_deep_analysis_returns_report_when_done(session: AsyncSession) -> None:
    owner, project, run = await _setup_done_run(session)
    analysis = await make_deep_analysis(session, run=run, requested_by=owner)
    analysis.status = DeepAnalysisStatus.done
    analysis.report_stats = {"topics": []}
    analysis.report_recommendations = {"content_ideas": []}
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/deep-analyses/{analysis.id}", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "done"
        assert body["report_stats"] == {"topics": []}
        assert body["report_recommendations"] == {"content_ideas": []}


async def test_get_deep_analysis_sums_comments_analyzed_count(session: AsyncSession) -> None:
    """The report page's summary card needs a total-comments-analyzed figure, which is not
    stored on DeepAnalysis itself -- aggregated here from its items."""
    owner, project, run = await _setup_done_run(session)
    analysis = await make_deep_analysis(session, run=run, requested_by=owner)
    items = await session.execute(select(ContentItem).where(ContentItem.run_id == run.id))
    item_a, item_b = [row[0] for row in items.all()]
    session.add_all(
        [
            DeepAnalysisItem(
                deep_analysis_id=analysis.id,
                content_item_id=item_a.id,
                status=DeepAnalysisItemStatus.done,
                comments_analyzed_count=5,
            ),
            DeepAnalysisItem(
                deep_analysis_id=analysis.id,
                content_item_id=item_b.id,
                status=DeepAnalysisItemStatus.done,
                comments_analyzed_count=2,
            ),
        ]
    )
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/deep-analyses/{analysis.id}", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        assert resp.json()["comments_analyzed_count"] == 7


async def test_get_deep_analysis_404_for_missing_or_foreign(session: AsyncSession) -> None:
    owner, project, run = await _setup_done_run(session)
    analysis = await make_deep_analysis(session, run=run, requested_by=owner)
    other_owner = await make_user(session)
    await make_workspace(session, owner=other_owner)
    await session.commit()

    async with await client(session) as c:
        missing = await c.get(f"/deep-analyses/{uuid.uuid4()}", headers=auth_headers(owner.id))
        assert missing.status_code == 404

        foreign = await c.get(f"/deep-analyses/{analysis.id}", headers=auth_headers(other_owner.id))
        assert foreign.status_code == 404
