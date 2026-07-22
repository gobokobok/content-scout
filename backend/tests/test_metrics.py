from src.config import Settings
from src.services.metrics import bucket_virality, virality_ratio


def _settings(**overrides: object) -> Settings:
    return Settings(**overrides)  # type: ignore[arg-type]


def test_virality_ratio_engagement_only_for_non_reel() -> None:
    # post/carousel: views is always None, so only the engagement ratio can apply.
    ratio = virality_ratio(
        likes=300, comments=50, views=None, median_engagement=100.0, median_views=None
    )
    assert ratio == (300 + 50) / 100.0


def test_virality_ratio_reel_takes_the_higher_of_engagement_and_views() -> None:
    # engagement_ratio = 150/100 = 1.5; view_ratio = 9000/1000 = 9.0 — reel wins via reach.
    ratio = virality_ratio(
        likes=100, comments=50, views=9000, median_engagement=100.0, median_views=1000.0
    )
    assert ratio == 9.0


def test_virality_ratio_reel_falls_back_to_engagement_when_views_baseline_missing() -> None:
    # account has no recorded view data yet (median_views is None) — engagement ratio still works.
    ratio = virality_ratio(
        likes=400, comments=0, views=9000, median_engagement=100.0, median_views=None
    )
    assert ratio == 4.0


def test_virality_ratio_none_when_no_engagement_baseline() -> None:
    # all-zero-engagement account: median_engagement is 0/None, no views either — no signal at all.
    assert (
        virality_ratio(likes=0, comments=0, views=None, median_engagement=None, median_views=None)
        is None
    )


def test_virality_ratio_treats_null_likes_and_comments_as_zero() -> None:
    ratio = virality_ratio(
        likes=None, comments=None, views=None, median_engagement=50.0, median_views=None
    )
    assert ratio == 0.0


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
