import time
from collections.abc import Callable

from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

API_PATH_PREFIXES = ("/auth", "/spaces", "/bookings", "/users", "/admin")

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds for API groups",
    ["method", "path_group", "status_class"],
    buckets=(0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1, 2, 5),
)

BOOKING_CREATE_ATTEMPTS_TOTAL = Counter(
    "booking_create_attempts_total",
    "Total booking creation attempts",
)

BOOKING_COLLISIONS_TOTAL = Counter(
    "booking_collisions_total",
    "Total booking collisions (slot already booked)",
)

BOOKING_CREATE_SUCCESS_TOTAL = Counter(
    "booking_create_success_total",
    "Total successful booking creations",
)


def get_api_group(path: str) -> str | None:
    for prefix in API_PATH_PREFIXES:
        if path == prefix or path.startswith(f"{prefix}/"):
            return prefix
    return None


class APIRequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path_group = get_api_group(request.url.path)
        if path_group is None:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        status_class = f"{response.status_code // 100}xx"
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method,
            path_group=path_group,
            status_class=status_class,
        ).observe(elapsed)

        return response
