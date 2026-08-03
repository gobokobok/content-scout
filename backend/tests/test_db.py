from unittest.mock import MagicMock, patch

from src.config import get_settings
from src.db import get_engine


def test_get_engine_passes_configured_pool_sizing() -> None:
    """E20-S2: explicit pool_size/max_overflow instead of SQLAlchemy's unconfigured default."""
    settings = get_settings()
    get_engine.cache_clear()
    try:
        with patch("src.db.create_async_engine") as mock_create:
            mock_create.return_value = MagicMock()
            get_engine()
    finally:
        get_engine.cache_clear()

    mock_create.assert_called_once()
    _, kwargs = mock_create.call_args
    assert kwargs["pool_size"] == settings.db_pool_size
    assert kwargs["max_overflow"] == settings.db_max_overflow
    assert kwargs["pool_pre_ping"] is True
