class EocError(Exception):
    """Base class for controlled application failures."""


class UpstreamSchemaError(EocError):
    """An upstream responded, but the response did not match its documented schema."""


class UpstreamUnavailableError(EocError):
    """An upstream could not be reached within its bounded acquisition policy."""


class CircuitOpenError(EocError):
    """Polling is paused because the source circuit breaker is open."""
