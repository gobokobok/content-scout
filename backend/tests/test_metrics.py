from src.config import Settings
from src.services.metrics import bucket_virality


def _settings(**overrides: object) -> Settings:
    return Settings(**overrides)  # type: ignore[arg-type]


def test_bucket_virality_high_above_threshold() -> None:
    assert bucket_virality(3.0, item_count=5, settings=_settings()) == "high"


def test_bucket_virality_high_threshold_is_inclusive() -> None:
    assert bucket_virality(2.0, item_count=5, settings=_settings()) == "high"


def test_bucket_virality_medium_between_thresholds() -> None:
    assert bucket_virality(1.0, item_count=5, settings=_settings()) == "medium"


def test_bucket_virality_low_threshold_is_exclusive_from_medium() -> None:
    # exactly at low_ratio (0.7) is NOT low — "low" is strictly below the threshold.
    assert bucket_virality(0.7, item_count=5, settings=_settings()) == "medium"


def test_bucket_virality_low_below_threshold() -> None:
    assert bucket_virality(0.5, item_count=5, settings=_settings()) == "low"


def test_bucket_virality_insufficient_items_returns_none() -> None:
    # default virality_min_items is 3
    assert bucket_virality(5.0, item_count=2, settings=_settings()) is None


def test_bucket_virality_none_ratio_returns_none() -> None:
    # e.g. an all-zero-engagement account (NULLIF(median, 0) makes the SQL ratio NULL)
    assert bucket_virality(None, item_count=5, settings=_settings()) is None


def test_bucket_virality_respects_custom_thresholds() -> None:
    settings = _settings(virality_high_ratio=3.0, virality_low_ratio=1.0, virality_min_items=1)
    assert bucket_virality(3.5, item_count=1, settings=settings) == "high"
    assert bucket_virality(2.5, item_count=1, settings=settings) == "medium"
    assert bucket_virality(0.9, item_count=1, settings=settings) == "low"
