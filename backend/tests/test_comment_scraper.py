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
    ApifyCommentsFailedError,
    BrightDataCommentsClient,
    fetch_comments,
    fetch_comments_batch,
)
from tests.conftest import make_content_item, make_user

APIFY_FIXTURE = Path(__file__).parent / "fixtures" / "apify_comments_sample.json"
BRIGHTDATA_FIXTURE = Path(__file__).parent / "fixtures" / "brightdata_comments_sample.json"


class _FakeActorClient:
    def __init__(self, run_result: object | None, raises: bool = False) -> None:
        self._run_result = run_result
        self._raises = raises
        self.call_kwargs: dict | None = None

    async def call(self, *, run_input, run_timeout, max_total_charge_usd, memory_mbytes):
        self.call_kwargs = {"run_input": run_input, "memory_mbytes": memory_mbytes}
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
    client._memory_mbytes = 256  # type: ignore[attr-defined]
    client._max_concurrent_actor_runs = 25  # type: ignore[attr-defined]
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
    assert actor_client.call_kwargs["run_input"]["maxItems"] == 25  # D41: was resultsLimit
    assert actor_client.call_kwargs["memory_mbytes"] == 256


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


# ── E20-S1: batched comment scraping ─────────────────────────────────────────────────────────


def _batch_comment_item(comment_id: str, post_url: str, likes: int) -> dict:
    return {
        "id": comment_id,
        "text": f"Комментарий {comment_id}",
        "ownerUsername": "someone",
        "likesCount": likes,
        "timestamp": "2026-07-20T12:00:00.000Z",
        "postUrl": post_url,
    }


async def test_apify_client_fetch_comments_batch_sends_batched_run_input() -> None:
    urls = ["https://instagram.com/p/a/", "https://instagram.com/p/b/"]
    items = [
        _batch_comment_item("c1", urls[0], 10),
        _batch_comment_item("c2", urls[1], 20),
    ]
    run_result = SimpleNamespace(default_dataset_id="dataset-1", status="SUCCEEDED")
    actor_client = _FakeActorClient(run_result)
    client = _apify_client_with(actor_client, _FakeDatasetClient(items))

    grouped = await client.fetch_comments_batch(urls, per_post_limit=15)

    assert actor_client.call_kwargs["run_input"]["startUrls"] == [
        {"url": urls[0]},
        {"url": urls[1]},
    ]
    assert actor_client.call_kwargs["run_input"]["maxItems"] == 30  # 2 posts * 15 per-post
    assert [c.external_id for c in grouped[urls[0]]] == ["c1"]
    assert [c.external_id for c in grouped[urls[1]]] == ["c2"]


async def test_apify_client_fetch_comments_batch_raises_when_nothing_matches() -> None:
    urls = ["https://instagram.com/p/a/", "https://instagram.com/p/b/"]
    # No postUrl/inputUrl/etc field at all — simulates every field-name guess being wrong.
    items = [{"id": "c1", "text": "x", "likesCount": 1, "timestamp": None}]
    run_result = SimpleNamespace(default_dataset_id="dataset-1", status="SUCCEEDED")
    client = _apify_client_with(_FakeActorClient(run_result), _FakeDatasetClient(items))

    try:
        await client.fetch_comments_batch(urls, per_post_limit=15)
        raise AssertionError("expected ApifyCommentsFailedError")
    except ApifyCommentsFailedError:
        pass


async def test_apify_client_fetch_comments_batch_partial_match_keeps_matched_posts() -> None:
    """One post's items fail to match (simulating a per-item quirk, not a systemic field-name
    miss) -- the matched post's comments are still trusted, same trust level as a single-post
    call returning genuinely zero comments."""
    urls = ["https://instagram.com/p/a/", "https://instagram.com/p/b/"]
    items = [
        _batch_comment_item("c1", urls[0], 10),
        {"id": "c2", "text": "unmatchable", "likesCount": 5, "timestamp": None},
    ]
    run_result = SimpleNamespace(default_dataset_id="dataset-1", status="SUCCEEDED")
    client = _apify_client_with(_FakeActorClient(run_result), _FakeDatasetClient(items))

    grouped = await client.fetch_comments_batch(urls, per_post_limit=15)

    assert [c.external_id for c in grouped[urls[0]]] == ["c1"]
    assert grouped[urls[1]] == []


async def test_fetch_comments_batch_groups_sorts_caps_and_records_usage_per_post(
    session: AsyncSession,
) -> None:
    user = await make_user(session)
    item_a = await make_content_item(session, url="https://instagram.com/p/a/")
    item_b = await make_content_item(session, url="https://instagram.com/p/b/")
    items = [
        _batch_comment_item("c1", item_a.url, 10),
        _batch_comment_item("c2", item_a.url, 90),
        _batch_comment_item("c3", item_b.url, 5),
    ]
    run_result = SimpleNamespace(default_dataset_id="dataset-1", status="SUCCEEDED")
    apify_client = _apify_client_with(_FakeActorClient(run_result), _FakeDatasetClient(items))

    result = await fetch_comments_batch(
        session,
        [item_a, item_b],
        user_id=user.id,
        settings=_settings(deep_analysis_comments_per_post=1),  # cap 1 -> keeps top-liked only
        apify_client=apify_client,
    )

    assert [c.external_id for c in result[item_a.id]] == ["c2"]  # 90 likes > 10, capped to 1
    assert [c.external_id for c in result[item_b.id]] == ["c3"]

    rows = (await session.scalars(select(UsageEvent))).all()
    # One KIND_APIFY_COMMENT_RESULT query row per post (quantity=1 each), no overage (cap=1
    # stays under apify_comment_included_comments).
    assert len(rows) == 2
    assert all(r.kind == KIND_APIFY_COMMENT_RESULT and r.quantity == 1 for r in rows)


async def test_fetch_comments_batch_falls_back_to_per_item_path_on_batch_failure(
    session: AsyncSession,
) -> None:
    """A batched-call failure (e.g. the whole actor run errors) falls back to the original
    per-item fetch_comments for every item -- Bright Data still covers each post individually."""
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
        result = await fetch_comments_batch(
            session,
            [item],
            user_id=user.id,
            settings=_settings(brightdata_api_token="tok", brightdata_ig_comments_dataset_id="ds1"),
            apify_client=apify_client,
        )

    assert len(result[item.id]) == 5
    rows = (await session.scalars(select(UsageEvent))).all()
    assert len(rows) == 1
    assert rows[0].kind == KIND_BRIGHTDATA_COMMENT_RESULT


async def test_fetch_comments_batch_empty_items_returns_empty_dict(session: AsyncSession) -> None:
    result = await fetch_comments_batch(
        session, [], user_id=(await make_user(session)).id, settings=_settings()
    )
    assert result == {}
