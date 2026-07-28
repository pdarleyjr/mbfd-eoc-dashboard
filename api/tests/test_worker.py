from unittest.mock import Mock

from app import worker
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


async def test_reconcile_configured_sources_uses_registry_ids(monkeypatch) -> None:
    captured: dict[str, set[str]] = {}
    session = object()

    class SessionContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *_args):
            return None

    class FakeRepository:
        def __init__(self, actual_session) -> None:
            assert actual_session is session

        async def retire_unconfigured_sources(self, source_ids: set[str]) -> None:
            captured["source_ids"] = source_ids

    monkeypatch.setattr(worker, "SessionFactory", SessionContext)
    monkeypatch.setattr(worker, "Repository", FakeRepository)

    await worker.reconcile_configured_sources(
        [Mock(source_id="configured-b"), Mock(source_id="configured-a")]
    )

    assert captured["source_ids"] == {"configured-a", "configured-b"}
