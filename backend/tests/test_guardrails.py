"""E7-S4: Pilot security guardrails — invite code, run quota, XLSX injection, timing fix."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.providers import email_password_provider
from src.auth.tokens import create_access_token
from src.config import Settings, get_settings
from src.db import get_session
from src.main import app
from src.models import AnalysisRun
from src.services.xlsx_export import _safe_text
from tests.conftest import (
    make_account,
    make_account_list,
    make_project,
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


async def _noop_rate_limit(*args, **kwargs) -> None:
    pass


# ---------------------------------------------------------------------------
# XLSX formula injection guard
# ---------------------------------------------------------------------------


def test_safe_text_passthrough_for_normal_values():
    assert _safe_text("hello") == "hello"
    assert _safe_text("") == ""
    assert _safe_text(None) == ""
    assert _safe_text("100") == "100"


def test_safe_text_prefixes_formula_triggers():
    assert _safe_text("=SUM(A1:B1)") == "'=SUM(A1:B1)"
    assert _safe_text("+1 (555) 123-4567") == "'+1 (555) 123-4567"
    assert _safe_text("-negative") == "'-negative"
    assert _safe_text("@username") == "'@username"


# ---------------------------------------------------------------------------
# Invite code
# ---------------------------------------------------------------------------


async def test_register_without_invite_when_not_required(session: AsyncSession) -> None:
    settings = get_settings()
    overridden = Settings(
        **{**settings.model_dump(), "registration_invite_code": ""}
    )
    with (
        patch("src.api.auth.get_settings", return_value=overridden),
        patch("src.api.auth.check_rate_limit", _noop_rate_limit),
    ):
        async with await _client(session) as c:
            resp = await c.post(
                "/auth/register",
                json={"email": f"u-{uuid.uuid4().hex[:8]}@test.com", "password": "password123"},
            )
    assert resp.status_code == 201


async def test_register_with_correct_invite_code(session: AsyncSession) -> None:
    settings = get_settings()
    overridden = Settings(**{**settings.model_dump(), "registration_invite_code": "secret42"})
    with (
        patch("src.api.auth.get_settings", return_value=overridden),
        patch("src.api.auth.check_rate_limit", _noop_rate_limit),
    ):
        async with await _client(session) as c:
            resp = await c.post(
                "/auth/register",
                json={
                    "email": f"u-{uuid.uuid4().hex[:8]}@test.com",
                    "password": "password123",
                    "invite_code": "secret42",
                },
            )
    assert resp.status_code == 201


async def test_register_with_wrong_invite_code_returns_400(session: AsyncSession) -> None:
    settings = get_settings()
    overridden = Settings(**{**settings.model_dump(), "registration_invite_code": "correct"})
    with (
        patch("src.api.auth.get_settings", return_value=overridden),
        patch("src.api.auth.check_rate_limit", _noop_rate_limit),
    ):
        async with await _client(session) as c:
            resp = await c.post(
                "/auth/register",
                json={
                    "email": f"u-{uuid.uuid4().hex[:8]}@test.com",
                    "password": "password123",
                    "invite_code": "wrong",
                },
            )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "invalid_invite_code"


async def test_register_with_missing_invite_code_returns_400(session: AsyncSession) -> None:
    settings = get_settings()
    overridden = Settings(**{**settings.model_dump(), "registration_invite_code": "required"})
    with (
        patch("src.api.auth.get_settings", return_value=overridden),
        patch("src.api.auth.check_rate_limit", _noop_rate_limit),
    ):
        async with await _client(session) as c:
            resp = await c.post(
                "/auth/register",
                json={"email": f"u-{uuid.uuid4().hex[:8]}@test.com", "password": "password123"},
            )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "invalid_invite_code"


async def test_register_config_returns_require_invite_flag(session: AsyncSession) -> None:
    settings = get_settings()
    with_invite = Settings(**{**settings.model_dump(), "registration_invite_code": "xyz"})
    without_invite = Settings(**{**settings.model_dump(), "registration_invite_code": ""})

    async with await _client(session) as c:
        with patch("src.api.auth.get_settings", return_value=with_invite):
            resp = await c.get("/auth/register/config")
        assert resp.json() == {"require_invite": True}

        with patch("src.api.auth.get_settings", return_value=without_invite):
            resp = await c.get("/auth/register/config")
        assert resp.json() == {"require_invite": False}


# ---------------------------------------------------------------------------
# Run quota
# ---------------------------------------------------------------------------


async def test_run_quota_blocks_on_limit(session: AsyncSession) -> None:
    user = await make_user(session)
    workspace = await make_workspace(session, owner=user)
    project = await make_project(session, workspace=workspace)
    account_list = await make_account_list(session, project=project)
    await make_account(session, account_list=account_list)
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(10):
        run = AnalysisRun(
            project_id=project.id,
            requested_by=user.id,
            duration_days=1,
            created_at=today_start + timedelta(minutes=i),
        )
        session.add(run)
    await session.commit()

    settings = get_settings()
    overridden = Settings(**{**settings.model_dump(), "max_runs_per_user_per_day": 10})
    with (
        patch("src.api.runs.get_settings", return_value=overridden),
        patch("src.api.auth.check_rate_limit", _noop_rate_limit),
    ):
        async with await _client(session) as c:
            resp = await c.post(
                f"/projects/{project.id}/runs",
                json={"duration_days": 1},
                headers=auth_headers(user.id),
            )

    assert resp.status_code == 429
    assert resp.json()["detail"]["code"] == "run_quota_exceeded"


# ---------------------------------------------------------------------------
# Login timing fix — user-not-found path must not short-circuit bcrypt
# ---------------------------------------------------------------------------


async def test_authenticate_returns_none_for_nonexistent_user(session: AsyncSession) -> None:
    result = await email_password_provider.authenticate(
        session, email="nobody@example.com", password="whatever"
    )
    assert result is None


# ---------------------------------------------------------------------------
# Rate limiter unit — mock Redis to avoid network dependency
# ---------------------------------------------------------------------------


async def test_rate_limit_blocks_after_threshold() -> None:
    from fastapi import HTTPException
    from starlette.datastructures import Headers
    from starlette.requests import Request

    from src.middleware.rate_limit import check_rate_limit

    call_count = 0

    async def _incr(_key: str) -> int:
        nonlocal call_count
        call_count += 1
        return call_count

    async def _expire(_key: str, _ttl: int) -> None:
        pass

    mock_redis = MagicMock()
    mock_redis.incr = _incr
    mock_redis.expire = _expire

    async def _get_mock_pool():
        return mock_redis

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/auth/login",
        "query_string": b"",
        "headers": Headers().raw,
    }

    with patch("src.middleware.rate_limit.get_redis_pool", _get_mock_pool):
        for _ in range(10):
            req = Request(scope)
            req._client = ("127.0.0.1", 9999)  # type: ignore[attr-defined]
            await check_rate_limit(req, limit=10)

        req = Request(scope)
        req._client = ("127.0.0.1", 9999)  # type: ignore[attr-defined]
        with pytest.raises(HTTPException) as exc_info:
            await check_rate_limit(req, limit=10)

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["code"] == "rate_limited"
