import uuid
from datetime import UTC, datetime, timedelta

from httpx import ASGITransport, AsyncClient
from openpyxl import load_workbook
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
    project = await make_project(session, workspace=ws, name="Test Project")
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list, handle="natgeo")
    run = await make_run(session, project=project, requested_by=owner)
    now = datetime.now(UTC)
    await make_content_item(
        session,
        run=run,
        account=account,
        type=ContentType.reel,
        published_at=now - timedelta(days=3),
        views=9000,
        likes=300,
        comments=42,
        title="Reel one",
    )
    await make_content_item(
        session,
        run=run,
        account=account,
        type=ContentType.carousel,
        published_at=now - timedelta(days=1),
        views=None,
        likes=100,
        title="Carousel two",
    )
    await session.commit()
    return owner, run


async def test_export_returns_xlsx(session: AsyncSession) -> None:
    owner, run = await _setup(session)
    async with await client(session) as c:
        resp = await c.get(f"/runs/{run.id}/export.xlsx", headers=auth_headers(owner.id))

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    cd = resp.headers["content-disposition"]
    assert "attachment" in cd
    assert "content-scout_" in cd
    assert ".xlsx" in cd


async def test_export_xlsx_has_russian_headers(session: AsyncSession) -> None:
    owner, run = await _setup(session)
    async with await client(session) as c:
        resp = await c.get(f"/runs/{run.id}/export.xlsx", headers=auth_headers(owner.id))

    import io

    wb = load_workbook(io.BytesIO(resp.content))
    ws = wb.active
    assert ws is not None
    headers = [ws.cell(1, col).value for col in range(1, 14)]
    assert headers[0] == "Аккаунт"
    assert headers[1] == "Подписчики"
    assert headers[5] == "Ссылка"
    assert headers[7] == "Лайки"
    assert headers[8] == "Просмотры"
    assert headers[9] == "Комментарии"


async def test_export_xlsx_data_and_hyperlink(session: AsyncSession) -> None:
    owner, run = await _setup(session)
    async with await client(session) as c:
        resp = await c.get(f"/runs/{run.id}/export.xlsx", headers=auth_headers(owner.id))

    import io

    wb = load_workbook(io.BytesIO(resp.content))
    ws = wb.active
    assert ws is not None

    # Two data rows + header
    assert ws.max_row == 3

    # Ссылка column (6) in row 2 should have a hyperlink
    url_cell = ws.cell(2, 6)
    assert url_cell.hyperlink is not None

    # Комментарии column (10) in row 2 (the reel with comments=42)
    assert ws.cell(2, 10).value == 42


async def test_export_404_for_wrong_user(session: AsyncSession) -> None:
    owner, run = await _setup(session)
    other = await make_user(session)
    await make_workspace(session, owner=other)
    await session.commit()
    async with await client(session) as c:
        resp = await c.get(f"/runs/{run.id}/export.xlsx", headers=auth_headers(other.id))
    assert resp.status_code == 404
