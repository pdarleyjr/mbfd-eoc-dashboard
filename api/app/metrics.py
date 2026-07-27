from prometheus_client import Counter, Gauge, Histogram

SOURCE_POLLS = Counter(
    "eoc_source_polls_total",
    "Source acquisition attempts",
    ["source_id", "outcome"],
)
SOURCE_POLL_SECONDS = Histogram(
    "eoc_source_poll_duration_seconds",
    "Source acquisition duration",
    ["source_id"],
)
SOURCE_RECORDS = Gauge(
    "eoc_source_records",
    "Current normalized records returned by a successful poll",
    ["source_id"],
)
SCHEDULER_LOCK = Gauge(
    "eoc_scheduler_lock_acquired",
    "Whether the current worker acquired a source lock",
    ["source_id"],
)
CACHE_EVENTS = Counter(
    "eoc_cache_events_total",
    "Dashboard cache invalidations",
    ["event"],
)
