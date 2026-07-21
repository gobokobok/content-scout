import os
import subprocess
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models import (
    Account,
    AccountList,
    AnalysisRun,
    ContentItem,
    ContentType,
    PlatformSlug,
    Project,
    User,
    Workspace,
    WorkspaceMember,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent

DEFAULT_TEST_DB_URL = "postgresql+asyncpg://scout:scout@localhost:5432/content_scout_test"


def _test_db_url() -> str:
    url = os.environ.get("DATABASE_URL", DEFAULT_TEST_DB_URL)
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url.removeprefix(prefix)
    return url


@pytest.fixture(autouse=True)
async def reset_singletons():
    """Reset event-loop-bound singletons before and after each test.

    pytest-asyncio uses a fresh event loop per test function. Module-level singletons
    that hold asyncio connections (Redis pool, SQLAlchemy engine) are bound to the loop
    they were created on; reusing them on a new loop raises 'Event loop is closed' or
    'got Future attached to a different loop'. Clearing before each test forces fresh
    creation on the current loop; disposing the engine after the test closes asyncpg
    connections cleanly before the loop goes away.
    """
    import src.db as _db
    import src.services.queue as _q

    _q._pool = None
    _db.get_engine.cache_clear()
    _db.get_sessionmaker.cache_clear()

    yield

    _q._pool = None
    if _db.get_engine.cache_info().currsize > 0:
        try:
            await _db.get_engine().dispose()
        except Exception:  # noqa: BLE001
            pass
    _db.get_engine.cache_clear()
    _db.get_sessionmaker.cache_clear()


@pytest.fixture(scope="session")
def migrated_db() -> str:
    """Run alembic upgrade head once per test session against the test DB."""
    url = _test_db_url()
    env = {**os.environ, "DATABASE_URL": url}
    subprocess.run(
        [
            str(BACKEND_DIR / ".venv" / "bin" / "alembic")
            if (BACKEND_DIR / ".venv").exists()
            else "alembic",
            "downgrade",
            "base",
        ],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            str(BACKEND_DIR / ".venv" / "bin" / "alembic")
            if (BACKEND_DIR / ".venv").exists()
            else "alembic",
            "upgrade",
            "head",
        ],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
        capture_output=True,
    )
    return url


@pytest.fixture
async def session(migrated_db: str) -> AsyncIterator[AsyncSession]:
    """A session inside an outer transaction that is always rolled back."""
    engine = create_async_engine(migrated_db)
    async with engine.connect() as conn:
        trans = await conn.begin()
        maker = async_sessionmaker(
            conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        async with maker() as sess:
            yield sess
        await trans.rollback()
    await engine.dispose()


# --- factories -------------------------------------------------------------


async def make_user(session: AsyncSession, **kw) -> User:
    kw.setdefault("token_balance", 1000)
    kw.setdefault("display_name", "Тест Тестов")
    user = User(email=kw.pop("email", f"u-{uuid.uuid4().hex[:10]}@example.com"), **kw)
    session.add(user)
    await session.flush()
    return user


async def make_workspace(session: AsyncSession, owner: User | None = None, **kw) -> Workspace:
    owner = owner or await make_user(session)
    ws = Workspace(name=kw.pop("name", "Личный"), **kw)
    session.add(ws)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=ws.id, user_id=owner.id))
    await session.flush()
    return ws


async def make_project(session: AsyncSession, workspace: Workspace | None = None, **kw) -> Project:
    workspace = workspace or await make_workspace(session)
    project = Project(workspace_id=workspace.id, name=kw.pop("name", "Мой блог"), **kw)
    session.add(project)
    await session.flush()
    return project


async def make_account_list(
    session: AsyncSession, project: Project | None = None, **kw
) -> AccountList:
    project = project or await make_project(session)
    account_list = AccountList(
        project_id=project.id, platform=kw.pop("platform", PlatformSlug.instagram), **kw
    )
    session.add(account_list)
    await session.flush()
    return account_list


async def make_account(
    session: AsyncSession, account_list: AccountList | None = None, **kw
) -> Account:
    account_list = account_list or await make_account_list(session)
    handle = kw.pop("handle", f"acc_{uuid.uuid4().hex[:8]}")
    account = Account(
        account_list_id=account_list.id,
        input_url=kw.pop("input_url", f"https://instagram.com/{handle}"),
        normalized_url=kw.pop("normalized_url", f"https://instagram.com/{handle}"),
        handle=handle,
        **kw,
    )
    session.add(account)
    await session.flush()
    return account


async def make_run(
    session: AsyncSession,
    project: Project | None = None,
    requested_by: User | None = None,
    **kw,
) -> AnalysisRun:
    project = project or await make_project(session)
    requested_by = requested_by or await make_user(session)
    run = AnalysisRun(
        project_id=project.id,
        requested_by=requested_by.id,
        duration_days=kw.pop("duration_days", 7),
        **kw,
    )
    session.add(run)
    await session.flush()
    return run


async def make_content_item(
    session: AsyncSession,
    run: AnalysisRun | None = None,
    account: Account | None = None,
    **kw,
) -> ContentItem:
    run = run or await make_run(session)
    account = account or await make_account(session)
    item = ContentItem(
        run_id=run.id,
        account_id=account.id,
        external_id=kw.pop("external_id", uuid.uuid4().hex[:12]),
        type=kw.pop("type", ContentType.reel),
        published_at=kw.pop("published_at", datetime.now(UTC) - timedelta(days=1)),
        url=kw.pop("url", f"https://instagram.com/reel/{uuid.uuid4().hex[:10]}/"),
        raw=kw.pop("raw", {}),
        **kw,
    )
    session.add(item)
    await session.flush()
    return item
