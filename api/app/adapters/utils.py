import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

from dateutil.parser import isoparse


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(
                value / 1000 if abs(value) > 10_000_000_000 else value,
                UTC,
            )
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str):
        try:
            parsed = isoparse(value)
            return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed
        except (TypeError, ValueError, OverflowError):
            return None
    return None


def stable_id(source_id: str, upstream_id: object) -> str:
    value = str(upstream_id).strip()
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
    return f"{source_id}:{digest}"


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def compact_text(value: object, maximum: int = 1000) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:maximum]
