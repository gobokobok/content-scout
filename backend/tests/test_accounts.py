import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tokens import create_access_token
from src.db import get_session
from src.main import app
from src.models import ContentItem, DeepAnalysisItem, ShortlistItem
from tests.conftest import (
    make_account,
    make_account_list,
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


async def test_remove_account_with_scrape_history_archives_not_deletes(
    session: AsyncSession,
) -> None:
    # content_items.account_id (and shortlist_items/deep_analysis_items one level further down
    # via content_item_id) has no ON DELETE cascade — a hard delete used to fail with an
    # unhandled IntegrityError. Removing a competitor now archives instead, so history survives.
    owner, project = await _setup_project(session)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list)
    run = await make_run(session, project=project, requested_by=owner)
    item = await make_content_item(session, run=run, account=account)
    analysis = await make_deep_analysis(session, run=run, requested_by=owner)

    session.add(ShortlistItem(project_id=project.id, content_item_id=item.id, added_by=owner.id))
    session.add(DeepAnalysisItem(deep_analysis_id=analysis.id, content_item_id=item.id))
    await session.commit()

    async with await client(session) as c:
        resp = await c.delete(
            f"/projects/{project.id}/accounts/{account.id}", headers=auth_headers(owner.id)
        )
        assert resp.status_code == 204

    await session.refresh(account)
    assert account.archived_at is not None
    assert (await session.scalar(select(ContentItem).where(ContentItem.id == item.id))) is not None
    assert (
        await session.scalar(select(ShortlistItem).where(ShortlistItem.content_item_id == item.id))
    ) is not None
    assert (
        await session.scalar(
            select(DeepAnalysisItem).where(DeepAnalysisItem.content_item_id == item.id)
        )
    ) is not None


@patch("src.api.accounts.enqueue_profile_fetch", new_callable=AsyncMock)
async def test_readding_archived_account_reactivates_it(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project(session)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/accounts",
            json={"entries": ["@comeback"]},
            headers=auth_headers(owner.id),
        )
        original_id = resp.json()["added"][0]["id"]

        resp = await c.delete(
            f"/projects/{project.id}/accounts/{original_id}", headers=auth_headers(owner.id)
        )
        assert resp.status_code == 204

        resp = await c.post(
            f"/projects/{project.id}/accounts",
            json={"entries": ["@comeback"]},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["added"]) == 1
        assert body["added"][0]["id"] == original_id
        assert body["total"] == 1

        resp = await c.get(f"/projects/{project.id}/accounts", headers=auth_headers(owner.id))
        assert [a["id"] for a in resp.json()] == [original_id]


@patch("src.api.accounts.enqueue_profile_fetch", new_callable=AsyncMock)
async def test_archived_accounts_dont_count_against_the_cap_trigger(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    # The DB-level 50-per-list safeguard trigger used to count all rows, so 50 archived
    # accounts (0 active) would still block a genuinely new INSERT — defeats archiving.
    owner, project = await _setup_project(session)
    account_list = await make_account_list(session, project=project)
    for _ in range(50):
        await make_account(session, account_list=account_list, archived_at=datetime.now(UTC))
    await session.commit()

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/accounts",
            json={"entries": ["@freshslot"]},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["added"]) == 1
        assert body["total"] == 1


# --- Direct bug fix (chat-reported, 2026-08-04): post-mode Analysis's auto-created accounts
# (Account.hidden) must not pollute the Конкуренты list/picker or the 50-per-list cap. ---


async def test_list_accounts_excludes_hidden(session: AsyncSession) -> None:
    owner, project = await _setup_project(session)
    account_list = await make_account_list(session, project=project)
    visible = await make_account(session, account_list=account_list, handle="real_competitor")
    await make_account(session, account_list=account_list, handle="shadow_account", hidden=True)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/projects/{project.id}/accounts", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        assert [a["id"] for a in resp.json()] == [str(visible.id)]


@patch("src.api.accounts.enqueue_profile_fetch", new_callable=AsyncMock)
async def test_readding_hidden_account_surfaces_it_as_real_competitor(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project(session)
    account_list = await make_account_list(session, project=project)
    shadow = await make_account(
        session,
        account_list=account_list,
        handle="shadow_account",
        normalized_url="https://instagram.com/shadow_account",
        hidden=True,
    )
    await session.commit()

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/accounts",
            json={"entries": ["@shadow_account"]},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 201
        body = resp.json()
        # Same row reused, not a duplicate — preserves any scrape history tied to it.
        assert body["added"][0]["id"] == str(shadow.id)
        assert body["total"] == 1

        resp = await c.get(f"/projects/{project.id}/accounts", headers=auth_headers(owner.id))
        assert [a["id"] for a in resp.json()] == [str(shadow.id)]

    await session.refresh(shadow)
    assert shadow.hidden is False


@patch("src.api.accounts.enqueue_profile_fetch", new_callable=AsyncMock)
async def test_hidden_accounts_dont_count_against_the_cap_trigger(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project(session)
    account_list = await make_account_list(session, project=project)
    for _ in range(50):
        await make_account(session, account_list=account_list, hidden=True)
    await session.commit()

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/accounts",
            json={"entries": ["@freshslot"]},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 201
        assert resp.json()["total"] == 1


async def test_accounts_scoped_to_owning_workspace(session: AsyncSession) -> None:
    owner, project = await _setup_project(session)
    other_user = await make_user(session)
    await make_workspace(session, owner=other_user)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/projects/{project.id}/accounts", headers=auth_headers(other_user.id))
        assert resp.status_code == 404
