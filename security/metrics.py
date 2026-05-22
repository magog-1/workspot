"""Prometheus metrics exposed by the security sidecar."""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

circuit_breaker_state = Gauge(
    "security_circuit_breaker_state",
    "Circuit breaker state: 0=CLOSED, 1=HALF-OPEN, 2=OPEN",
)
fallback_requests_total = Counter(
    "security_fallback_requests_total",
    "Total requests handled in fallback mode",
)
auth_failures_total = Counter(
    "security_auth_failures_total",
    "Total auth check failures",
)
cache_hits_total = Counter(
    "security_cache_hits_total",
    "Cache hits",
)
cache_misses_total = Counter(
    "security_cache_misses_total",
    "Cache misses",
)


_STATE_VALUES = {"CLOSED": 0, "HALF-OPEN": 1, "OPEN": 2}


def set_state_metric(state: str) -> None:
    circuit_breaker_state.set(_STATE_VALUES.get(state, 0))


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
