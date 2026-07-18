import pytest

from src.services.url_normalizer import InvalidAccountUrlError, normalize_instagram_input


@pytest.mark.parametrize(
    "raw,expected_handle",
    [
        ("@blogger", "blogger"),
        ("blogger", "blogger"),
        ("Blogger", "blogger"),
        ("instagram.com/blogger", "blogger"),
        ("https://instagram.com/blogger", "blogger"),
        ("https://www.instagram.com/blogger/", "blogger"),
        ("https://www.instagram.com/blogger?igsh=abc123", "blogger"),
        ("http://instagram.com/blogger/", "blogger"),
        ("blog.ger_1", "blog.ger_1"),
    ],
)
def test_normalize_valid_inputs(raw: str, expected_handle: str) -> None:
    result = normalize_instagram_input(raw)
    assert result.handle == expected_handle
    assert result.normalized_url == f"https://instagram.com/{expected_handle}"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "https://facebook.com/blogger",
        "https://instagram.com/p/CxYz123/",
        "https://instagram.com/reel/CxYz123/",
        "https://instagram.com/",
        ".leadingdot",
        "trailingdot.",
        "way-too-long-handle-that-exceeds-the-thirty-char-limit",
        "bad handle with spaces",
    ],
)
def test_normalize_invalid_inputs_raise(raw: str) -> None:
    with pytest.raises(InvalidAccountUrlError):
        normalize_instagram_input(raw)
