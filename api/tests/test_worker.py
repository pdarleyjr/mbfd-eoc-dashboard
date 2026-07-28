from unittest.mock import Mock

from app.worker import (
    MAX_MISFIRE_GRACE_SECONDS,
    MIN_MISFIRE_GRACE_SECONDS,
    misfire_grace_seconds,
)


def test_misfire_grace_has_safe_minimum() -> None:
    adapter = Mock(timeout_seconds=5, retry_count=0)

    assert misfire_grace_seconds(adapter) == MIN_MISFIRE_GRACE_SECONDS


def test_misfire_grace_covers_retries_and_is_bounded() -> None:
    adapter = Mock(timeout_seconds=120, retry_count=2)
    very_slow_adapter = Mock(timeout_seconds=900, retry_count=3)

    assert misfire_grace_seconds(adapter) == 370
    assert misfire_grace_seconds(very_slow_adapter) == MAX_MISFIRE_GRACE_SECONDS
