import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models import KIND_APIFY_COMMENT_RESULT, KIND_BRIGHTDATA_COMMENT_RESULT, UsageEvent
from src.services.comment_scraper import (
    ApifyCommentsClient,
    BrightDataCommentsClient,
    fetch_comments,
)
from tests.conftest import make_content_item, make_user

APIFY_FIXTURE = Path(__file__).parent / "fixtures" / "apify_comments_sample.json"
BRIGHTDATA_FIXTURE = Path(__file__).parent / "fixtures" / "brightdata_comments_sample.json"


class _FakeActorClient:
    def __init__(self, run_result: object | None, raises: bool = False) -> None:
        self._run_result = run_result
        self._raises = raises
        self.call_kwargs: dict | None = None

    async def call(self, *, run_input, run_timeout, max_total_charge_usd):
        self.call_kwargs = {"run_input": run_input}
        if self._raises:
            raise RuntimeError("apidojo boom")
        return self._run_result


class _FakeDatasetClient:
    def __init__(self, items: list[dict]) -> None:
        self._items = items

    async def list_items(self):
        return SimpleNamespace(items=self._items)


def _apify_client_with(actor_client, dataset_client=None) -> ApifyCommentsClient:
    client = ApifyCommentsClient.__new__(ApifyCommentsClient)
    client._client = SimpleNamespace(  # type: ignore[attr-defined]
        actor=lambda _id: actor_client, dataset=lambda _id: dataset_client
    )
    client._actor_id = "apidojo/instagram-comments-scraper-api"  # type: ignore[attr-defined]
    client._max_charge_usd = Decimal("0.5")  # type: ignore[attr-defined]
    return client


def _settings(**overrides) -> Settings:
    return Settings(**overrides)


async def test_apify_client_normalizes_and_passes_limit() -> None:
    items = json.loads(APIFY_FIXTURE.read_text())
    run_result = SimpleNamespace(default_dataset_id="dataset-1", status="SUCCEEDED")
    actor_client = _FakeActorClient(run_result)
    client = _apify_client_with(actor_client, _FakeDatasetClient(items))

    comments = await client.fetch_comments("https://instagram.com/p/abc/", 25)

    assert len(comments) == 18
    assert actor_client.call_kwargs is not None
    assert actor_client.call_kwargs["run_input"]["startUrls"] == [
        {"url": "https://instagram.com/p/abc/"}
    ]
    assert actor_client.call_kwargs["run_input"]["resultsLimit"] == 25


async def test_fetch_comments_uses_apify_primary_sorts_by_likes_and_records_usage(
    session: AsyncSession,
) -> None:
    user = await make_user(session)
    item = await make_content_item(session, url="https://instagram.com/p/abc/")
    items = json.loads(APIFY_FIXTURE.read_text())
    run_result = SimpleNamespace(default_dataset_id="dataset-1", status="SUCCEEDED")
    apify_client = _apify_client_with(_FakeActorClient(run_result), _FakeDatasetClient(items))

    comments = await fetch_comments(
        session,
        item,
        user_id=user.id,
        settings=_settings(deep_analysis_comments_per_post=25),
        apify_client=apify_client,
    )

    assert len(comments) == 18
    assert comments[0].external_id == "c_apify_013"  # highest likesCount in the fixture (456)
    assert comments[0].likes == 456
    assert all(comments[i].likes >= comments[i + 1].likes for i in range(len(comments) - 1))

    rows = (await session.scalars(select(UsageEvent))).all()
    assert len(rows) == 2
    query_row = next(r for r in rows if r.quantity == 1)
    overage_row = next(r for r in rows if r.quantity != 1)
    assert query_row.kind == KIND_APIFY_COMMENT_RESULT
    assert overage_row.kind == KIND_APIFY_COMMENT_RESULT
    assert overage_row.quantity == 3  # 18 comments - 15 included


async def test_fetch_comments_falls_back_to_brightdata_on_apify_failure(
    session: AsyncSession,
) -> None:
    user = await make_user(session)
    item = await make_content_item(session, url="https://instagram.com/p/abc/")
    apify_client = _apify_client_with(_FakeActorClient(None, raises=True))

    bd_items = json.loads(BRIGHTDATA_FIXTURE.read_text())
    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    trigger_resp = MagicMock()
    trigger_resp.raise_for_status = MagicMock()
    trigger_resp.json = MagicMock(return_value={"snapshot_id": "snap1"})
    progress_resp = MagicMock()
    progress_resp.raise_for_status = MagicMock()
    progress_resp.json = MagicMock(return_value={"status": "ready"})
    snapshot_resp = MagicMock()
    snapshot_resp.raise_for_status = MagicMock()
    snapshot_resp.json = MagicMock(return_value=bd_items)
    mock_http.post = AsyncMock(return_value=trigger_resp)
    mock_http.get = AsyncMock(side_effect=[progress_resp, snapshot_resp])

    with (
        patch("src.services.comment_scraper.asyncio.sleep", new_callable=AsyncMock),
        patch("src.services.comment_scraper.httpx.AsyncClient", return_value=mock_http),
    ):
        comments = await fetch_comments(
            session,
            item,
            user_id=user.id,
            settings=_settings(brightdata_api_token="tok", brightdata_ig_comments_dataset_id="ds1"),
            apify_client=apify_client,
        )

    assert len(comments) == 5
    assert comments[0].external_id == "c_bd_003"  # highest likes (10) in the fixture
    rows = (await session.scalars(select(UsageEvent))).all()
    assert len(rows) == 1
    assert rows[0].kind == KIND_BRIGHTDATA_COMMENT_RESULT
    assert rows[0].quantity == 1


async def test_fetch_comments_returns_empty_and_no_usage_when_both_vendors_fail(
    session: AsyncSession,
) -> None:
    user = await make_user(session)
    item = await make_content_item(session, url="https://instagram.com/p/abc/")
    apify_client = _apify_client_with(_FakeActorClient(None, raises=True))

    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.post = AsyncMock(side_effect=RuntimeError("brightdata boom"))

    with (
        patch("src.services.comment_scraper.asyncio.sleep", new_callable=AsyncMock),
        patch("src.services.comment_scraper.httpx.AsyncClient", return_value=mock_http),
    ):
        comments = await fetch_comments(
            session,
            item,
            user_id=user.id,
            settings=_settings(brightdata_api_token="tok", brightdata_ig_comments_dataset_id="ds1"),
            apify_client=apify_client,
        )

    assert comments == []
    rows = (await session.scalars(select(UsageEvent))).all()
    assert rows == []


async def test_brightdata_client_sends_url_and_limit() -> None:
    client = BrightDataCommentsClient.__new__(BrightDataCommentsClient)
    client._token = "tok"  # type: ignore[attr-defined]
    client._base_url = "https://api.brightdata.com"  # type: ignore[attr-defined]
    client._dataset_id = "ds1"  # type: ignore[attr-defined]

    bd_items = json.loads(BRIGHTDATA_FIXTURE.read_text())
    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    trigger_resp = MagicMock()
    trigger_resp.raise_for_status = MagicMock()
    trigger_resp.json = MagicMock(return_value={"snapshot_id": "snap1"})
    progress_resp = MagicMock()
    progress_resp.raise_for_status = MagicMock()
    progress_resp.json = MagicMock(return_value={"status": "ready"})
    snapshot_resp = MagicMock()
    snapshot_resp.raise_for_status = MagicMock()
    snapshot_resp.json = MagicMock(return_value=bd_items)
    mock_http.post = AsyncMock(return_value=trigger_resp)
    mock_http.get = AsyncMock(side_effect=[progress_resp, snapshot_resp])

    with patch("src.services.comment_scraper.httpx.AsyncClient", return_value=mock_http):
        comments = await client.fetch_comments("https://instagram.com/p/xyz/", 25)

    assert len(comments) == 5
    post_call = mock_http.post.call_args
    assert post_call.kwargs["json"] == [{"url": "https://instagram.com/p/xyz/", "limit": 25}]
