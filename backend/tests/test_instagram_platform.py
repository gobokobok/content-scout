import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.models import Account, ContentType
from src.platforms.instagram import InstagramPlatform

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "apify_ig_sample.json"


def _account() -> Account:
    return Account(
        account_list_id=uuid.uuid4(),
        input_url="https://instagram.com/testuser",
        normalized_url="https://instagram.com/testuser",
        handle="testuser",
    )


class _FakeActorClient:
    def __init__(self, run_result: object) -> None:
        self._run_result = run_result
        self.call_kwargs: dict | None = None

    async def call(self, *, run_input, run_timeout, max_total_charge_usd):
        self.call_kwargs = {
            "run_input": run_input,
            "run_timeout": run_timeout,
            "max_total_charge_usd": max_total_charge_usd,
        }
        return self._run_result


class _FakeDatasetClient:
    def __init__(self, items: list[dict]) -> None:
        self._items = items

    async def list_items(self):
        return SimpleNamespace(items=self._items)


def _platform_with(actor_client, dataset_client=None) -> InstagramPlatform:
    platform = InstagramPlatform.__new__(InstagramPlatform)
    platform._client = SimpleNamespace(  # type: ignore[attr-defined]
        actor=lambda _id: actor_client,
        dataset=lambda _id: dataset_client,
    )
    platform._actor_id = "apify/instagram-scraper"  # type: ignore[attr-defined]
    platform._max_charge_usd = Decimal("0.5")  # type: ignore[attr-defined]
    return platform


async def test_fetch_content_normalizes_fixture() -> None:
    items = json.loads(FIXTURE_PATH.read_text())
    run_result = SimpleNamespace(default_dataset_id="dataset-1", status="SUCCEEDED")
    platform = _platform_with(_FakeActorClient(run_result), _FakeDatasetClient(items))

    result = await platform.fetch_content(_account(), datetime.now(UTC) - timedelta(days=3))

    assert len(result) == 3
    reel, post, carousel = result

    assert reel.type == ContentType.reel
    assert reel.views == 20000
    assert reel.likes == 1500
    assert reel.title == "A day in the life"
    assert reel.published_at == datetime(2026, 7, 15, 10, 0, tzinfo=UTC)

    assert post.type == ContentType.post
    assert post.views is None  # D14: no view counts for non-reel types
    assert post.title == "Single photo post"

    assert carousel.type == ContentType.carousel
    assert carousel.views is None
    assert carousel.title is None  # missing caption handled gracefully


async def test_fetch_content_passes_since_and_url() -> None:
    items = json.loads(FIXTURE_PATH.read_text())
    run_result = SimpleNamespace(default_dataset_id="dataset-1", status="SUCCEEDED")
    actor_client = _FakeActorClient(run_result)
    platform = _platform_with(actor_client, _FakeDatasetClient(items))

    account = _account()
    since = datetime(2026, 7, 10, tzinfo=UTC)
    await platform.fetch_content(account, since)

    assert actor_client.call_kwargs is not None
    run_input = actor_client.call_kwargs["run_input"]
    assert run_input["directUrls"] == [account.normalized_url]
    assert run_input["onlyPostsNewerThan"] == "2026-07-10"
    # Regression: an unset max_total_charge_usd lets Apify auto-reserve the whole remaining
    # account balance per run, so a second concurrent run can never start (stuck in READY).
    assert actor_client.call_kwargs["max_total_charge_usd"] == Decimal("0.5")


async def test_fetch_content_treats_error_placeholder_as_failure() -> None:
    run_result = SimpleNamespace(default_dataset_id="dataset-1", status="SUCCEEDED")
    error_item = {
        "url": "https://instagram.com/blocked",
        "error": "no_items",
        "errorDescription": "Empty or private data for provided input",
    }
    platform = _platform_with(_FakeActorClient(run_result), _FakeDatasetClient([error_item]))

    with patch("src.platforms.instagram.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(Exception, match="Empty or private data"):
            await platform.fetch_content(_account(), datetime.now(UTC) - timedelta(days=1))


async def test_fetch_content_treats_non_succeeded_status_as_failure() -> None:
    """An aborted/failed/timed-out Apify run must not be treated as 'zero new content'."""
    run_result = SimpleNamespace(default_dataset_id="dataset-1", status="TIMED-OUT")
    platform = _platform_with(_FakeActorClient(run_result), _FakeDatasetClient([]))

    with patch("src.platforms.instagram.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(Exception, match="TIMED-OUT"):
            await platform.fetch_content(_account(), datetime.now(UTC) - timedelta(days=1))


async def test_fetch_content_retries_then_raises() -> None:
    class _AlwaysFailActor:
        def __init__(self) -> None:
            self.attempts = 0

        async def call(self, *, run_input, run_timeout, max_total_charge_usd):
            self.attempts += 1
            raise RuntimeError("apify boom")

    actor = _AlwaysFailActor()
    platform = _platform_with(actor)

    with patch("src.platforms.instagram.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RuntimeError, match="apify boom"):
            await platform.fetch_content(_account(), datetime.now(UTC) - timedelta(days=1))

    assert actor.attempts == 3
