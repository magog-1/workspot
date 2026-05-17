"""Security sidecar — HTTP proxy with circuit breaker and fallback policy."""

from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, Request, Response
from jose import JWTError

from security.audit import log_decision
from security.circuit_breaker import CircuitBreaker
from security.metrics import (
    auth_failures_total,
    cache_hits_total,
    cache_misses_total,
    fallback_requests_total,
    render_metrics,
    set_state_metric,
)
from security.policy import (
    check_fallback_access,
    decode_jwt_role,
    get_cached_role,
    set_cached_role,
)

APP_URL = os.environ.get("APP_URL", "http://app:8000")
AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", APP_URL)
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production-min-32-chars!!")
CIRCUIT_BREAKER_THRESHOLD = int(os.environ.get("CIRCUIT_BREAKER_THRESHOLD", "5"))
CIRCUIT_BREAKER_TIMEOUT = int(os.environ.get("CIRCUIT_BREAKER_TIMEOUT", "60"))
UPSTREAM_TIMEOUT = float(os.environ.get("UPSTREAM_TIMEOUT", "5"))

breaker = CircuitBreaker(threshold=CIRCUIT_BREAKER_THRESHOLD, timeout=CIRCUIT_BREAKER_TIMEOUT)

app = FastAPI(title="WorkSpot Security Sidecar", version="1.0.0")


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return request.cookies.get("access_token")


def _identify(request: Request) -> tuple[str | None, str | None, str | None]:
    """Return (user_id, role, reason).

    ``reason`` is set when identification failed.
    """
    token = _extract_token(request)
    if not token:
        return None, None, "no_token"
    try:
        user_id, role = decode_jwt_role(token, JWT_SECRET)
    except JWTError as exc:
        auth_failures_total.inc()
        return None, None, f"jwt_error:{exc}"
    cached = get_cached_role(user_id)
    if cached:
        cache_hits_total.inc()
        role = cached
    else:
        cache_misses_total.inc()
        set_cached_role(user_id, role)
    return user_id, role, None


@app.get("/health")
async def health() -> dict[str, str]:
    state = breaker.get_state()
    set_state_metric(state)
    return {"status": "ok", "circuit_breaker": state}


@app.get("/metrics")
async def metrics() -> Response:
    set_state_metric(breaker.get_state())
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
)
async def proxy(path: str, request: Request) -> Response:
    user_id, role, ident_reason = _identify(request)
    state = breaker.get_state()
    set_state_metric(state)
    method = request.method
    resource = f"/{path}"

    # In OPEN state — apply fallback policy without contacting the app.
    if state == "OPEN":
        fallback_requests_total.inc()
        if not role:
            log_decision(
                user_id, role, method, resource, "deny",
                f"fallback_no_identity:{ident_reason}", state,
            )
            return Response(status_code=401, content="Unauthorized (fallback)")
        if not check_fallback_access(role, method):
            log_decision(
                user_id, role, method, resource, "deny",
                "fallback_method_blocked", state,
            )
            return Response(status_code=403, content="Forbidden (fallback policy)")
        log_decision(user_id, role, method, resource, "allow", "fallback_allowed", state)
        return await _forward(request, path, fallback=True)

    # CLOSED or HALF-OPEN: try full validation, then proxy.
    if state == "HALF-OPEN":
        log_decision(user_id, role, method, resource, "probe", "half_open_probe", state)

    try:
        response = await _forward(request, path, fallback=False)
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
        breaker.record_failure()
        new_state = breaker.get_state()
        set_state_metric(new_state)
        log_decision(
            user_id, role, method, resource, "deny",
            f"upstream_error:{type(exc).__name__}", new_state,
        )
        return Response(status_code=502, content="Upstream unavailable")

    if response.status_code >= 500:
        breaker.record_failure()
    else:
        breaker.record_success()
    set_state_metric(breaker.get_state())
    return response


async def _forward(request: Request, path: str, *, fallback: bool) -> Response:
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    url = f"{APP_URL}/{path}"
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
        upstream = await client.request(
            request.method,
            url,
            content=body,
            headers=headers,
            params=request.query_params,
        )
    response_headers = {
        k: v
        for k, v in upstream.headers.items()
        if k.lower() not in {"content-encoding", "transfer-encoding", "content-length", "connection"}
    }
    if fallback:
        response_headers["X-Security-Fallback"] = "true"
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
