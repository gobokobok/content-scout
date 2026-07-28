import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tokens import create_access_token
from src.db import get_session
from src.main import app
from src.models import (
    KIND_APIFY_RESULT,
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
    DeepAnalysisItem,
    DeepAnalysisItemStatus,
    UsageEvent,
)
from src.services.usage import rollup_run_totals
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


async def _client(session: AsyncSession) -> _TestClient:
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    return _TestClient(transport=transport, base_url="http://test")


def auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


async def make_usage_event(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
    kind: str,
    quantity: int,
    unit_cost_usd: Decimal,
    created_at: datetime | None = None,
) -> UsageEvent:
    ev = UsageEvent(
        user_id=user_id,
        run_id=run_id,
        kind=kind,
        quantity=quantity,
        unit_cost_usd=unit_cost_usd,
        created_at=created_at or datetime.now(UTC),
    )
    session.add(ev)
    return ev


def _url(from_: datetime, to: datetime) -> str:
    # URL-encode + in timezone offset (+00:00 → %2B00:00) so FastAPI parses correctly
    f = from_.isoformat().replace("+", "%2B")
    t = to.isoformat().replace("+", "%2B")
    return f"/me/usage?from={f}&to={t}"


def _runs_url(from_: datetime, to: datetime) -> str:
    f = from_.isoformat().replace("+", "%2B")
    t = to.isoformat().replace("+", "%2B")
    return f"/me/runs?from={f}&to={t}"


async def test_rollup_run_totals_sums_all_kinds_into_cost_and_claude_kinds_into_tokens(
    session: AsyncSession,
) -> None:
    run = await make_run(session)
    session.add_all(
        [
            UsageEvent(
                user_id=run.requested_by,
                run_id=run.id,
                kind=KIND_APIFY_RESULT,
                quantity=10,
                unit_cost_usd=Decimal("0.01"),
            ),
            UsageEvent(
                user_id=run.requested_by,
                run_id=run.id,
                kind=KIND_CLAUDE_INPUT_TOKENS,
                quantity=1000,
                unit_cost_usd=Decimal("0.000001"),
            ),
            UsageEvent(
                user_id=run.requested_by,
                run_id=run.id,
                kind=KIND_CLAUDE_OUTPUT_TOKENS,
                quantity=200,
                unit_cost_usd=Decimal("0.000005"),
            ),
        ]
    )
    await session.commit()

    await rollup_run_totals(session, run)

    assert run.total_input_tokens == 1000
    assert run.total_output_tokens == 200
    # 10*0.01 + 1000*0.000001 + 200*0.000005 = 0.1 + 0.001 + 0.001
    assert run.total_cost_usd == Decimal("0.102000")


async def test_rollup_run_totals_zero_when_no_usage(session: AsyncSession) -> None:
    run = await make_run(session)
    await session.commit()

    await rollup_run_totals(session, run)

    assert run.total_input_tokens == 0
    assert run.total_output_tokens == 0
    assert run.total_cost_usd == Decimal("0")


# --- GET /me/usage endpoint tests ---


async def test_usage_endpoint_empty(session: AsyncSession) -> None:
    user = await make_user(session)
    await session.commit()

    now = datetime.now(UTC)
    async with await _client(session) as c:
        resp = await c.get(
            _url(now - timedelta(days=30), now + timedelta(days=1)), headers=auth_headers(user.id)
        )
        assert resp.status_code == 200
        body = resp.json()
        assert Decimal(body["total_cost_usd"]) == Decimal("0")
        assert body["by_kind"] == []


async def test_usage_endpoint_totals(session: AsyncSession) -> None:
    user = await make_user(session)
    ws = await make_workspace(session, owner=user)
    project = await make_project(session, workspace=ws)
    run = await make_run(session, project=project, requested_by=user)
    now = datetime.now(UTC)

    await make_usage_event(
        session,
        user_id=user.id,
        run_id=run.id,
        kind=KIND_APIFY_RESULT,
        quantity=10,
        unit_cost_usd=Decimal("0.00030000"),
        created_at=now - timedelta(days=1),
    )
    await make_usage_event(
        session,
        user_id=user.id,
        run_id=run.id,
        kind=KIND_CLAUDE_INPUT_TOKENS,
        quantity=5000,
        unit_cost_usd=Decimal("0.00000025"),
        created_at=now - timedelta(days=1),
    )
    await make_usage_event(
        session,
        user_id=user.id,
        run_id=run.id,
        kind=KIND_CLAUDE_OUTPUT_TOKENS,
        quantity=500,
        unit_cost_usd=Decimal("0.00000125"),
        created_at=now - timedelta(days=1),
    )
    await session.commit()

    async with await _client(session) as c:
        resp = await c.get(
            _url(now - timedelta(days=30), now + timedelta(days=1)), headers=auth_headers(user.id)
        )
        assert resp.status_code == 200
        body = resp.json()

        by_kind = {e["kind"]: e for e in body["by_kind"]}
        assert by_kind[KIND_APIFY_RESULT]["quantity"] == 10
        assert by_kind[KIND_CLAUDE_INPUT_TOKENS]["quantity"] == 5000
        assert by_kind[KIND_CLAUDE_OUTPUT_TOKENS]["quantity"] == 500

        expected = (
            Decimal("10") * Decimal("0.00030000")
            + Decimal("5000") * Decimal("0.00000025")
            + Decimal("500") * Decimal("0.00000125")
        )
        assert Decimal(body["total_cost_usd"]) == expected


async def test_usage_endpoint_respects_date_range(session: AsyncSession) -> None:
    user = await make_user(session)
    await make_workspace(session, owner=user)
    now = datetime.now(UTC)

    await make_usage_event(
        session,
        user_id=user.id,
        kind=KIND_APIFY_RESULT,
        quantity=5,
        unit_cost_usd=Decimal("0.00030000"),
        created_at=now - timedelta(days=5),
    )
    # outside range
    await make_usage_event(
        session,
        user_id=user.id,
        kind=KIND_APIFY_RESULT,
        quantity=100,
        unit_cost_usd=Decimal("0.00030000"),
        created_at=now - timedelta(days=40),
    )
    await session.commit()

    async with await _client(session) as c:
        resp = await c.get(
            _url(now - timedelta(days=30), now + timedelta(days=1)), headers=auth_headers(user.id)
        )
        body = resp.json()
        by_kind = {e["kind"]: e for e in body["by_kind"]}
        assert by_kind[KIND_APIFY_RESULT]["quantity"] == 5


async def test_usage_endpoint_isolated_per_user(session: AsyncSession) -> None:
    user_a = await make_user(session)
    user_b = await make_user(session)
    now = datetime.now(UTC)

    await make_usage_event(
        session,
        user_id=user_a.id,
        kind=KIND_APIFY_RESULT,
        quantity=20,
        unit_cost_usd=Decimal("0.00030000"),
        created_at=now - timedelta(days=1),
    )
    await session.commit()

    async with await _client(session) as c:
        resp = await c.get(
            _url(now - timedelta(days=30), now + timedelta(days=1)), headers=auth_headers(user_b.id)
        )
        body = resp.json()
        assert Decimal(body["total_cost_usd"]) == Decimal("0")
        assert body["by_kind"] == []


async def test_usage_endpoint_response_shape(session: AsyncSession) -> None:
    user = await make_user(session)
    now = datetime.now(UTC)
    await make_usage_event(
        session,
        user_id=user.id,
        kind=KIND_APIFY_RESULT,
        quantity=1,
        unit_cost_usd=Decimal("0.00030000"),
        created_at=now - timedelta(days=1),
    )
    await session.commit()

    async with await _client(session) as c:
        resp = await c.get(
            _url(now - timedelta(days=30), now + timedelta(days=1)), headers=auth_headers(user.id)
        )
        body = resp.json()
        assert set(body.keys()) == {"from_", "to", "total_cost_usd", "by_kind"}
        entry = body["by_kind"][0]
        assert set(entry.keys()) == {"kind", "quantity", "cost_usd"}


# --- GET /me/runs endpoint tests ---


async def test_my_runs_includes_both_runs_and_deep_analyses(session: AsyncSession) -> None:
    user = await make_user(session)
    ws = await make_workspace(session, owner=user)
    project = await make_project(session, workspace=ws)
    now = datetime.now(UTC)

    run = await make_run(
        session,
        project=project,
        requested_by=user,
        status="done",
        progress_items=4,
        created_at=now - timedelta(hours=2),
    )
    analysis = await make_deep_analysis(
        session,
        run=run,
        requested_by=user,
        tokens_charged=60,
        status="failed",
        created_at=now - timedelta(hours=1),
    )
    await session.commit()

    async with await _client(session) as c:
        resp = await c.get(
            _runs_url(now - timedelta(days=1), now + timedelta(days=1)),
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 200
        body = resp.json()

    by_id = {e["id"]: e for e in body}
    assert by_id[str(run.id)]["kind"] == "run"
    assert by_id[str(run.id)]["tokens_charged"] == 4
    assert by_id[str(analysis.id)]["kind"] == "deep_analysis"
    assert by_id[str(analysis.id)]["tokens_charged"] == 60
    assert by_id[str(analysis.id)]["status"] == "failed"
    # most recent first
    assert [e["id"] for e in body] == [str(analysis.id), str(run.id)]


async def test_my_runs_sums_comments_analyzed_count_for_deep_analysis(
    session: AsyncSession,
) -> None:
    user = await make_user(session)
    ws = await make_workspace(session, owner=user)
    project = await make_project(session, workspace=ws)
    now = datetime.now(UTC)

    run = await make_run(session, project=project, requested_by=user, status="done")
    item_a = await make_content_item(session, run=run)
    item_b = await make_content_item(session, run=run)
    analysis = await make_deep_analysis(session, run=run, requested_by=user, created_at=now)
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

    async with await _client(session) as c:
        resp = await c.get(
            _runs_url(now - timedelta(days=1), now + timedelta(days=1)),
            headers=auth_headers(user.id),
        )
        assert resp.status_code == 200
        body = resp.json()

    by_id = {e["id"]: e for e in body}
    assert by_id[str(analysis.id)]["comments_analyzed_count"] == 7
    assert by_id[str(run.id)]["comments_analyzed_count"] is None
