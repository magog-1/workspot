"""Unit tests for the security sidecar (circuit breaker, policy, audit)."""

from __future__ import annotations

import time

from jose import jwt


def test_circuit_breaker_transitions() -> None:
    from security.circuit_breaker import CircuitBreaker

    cb = CircuitBreaker(threshold=3, timeout=60)
    assert cb.get_state() == "CLOSED"
    cb.record_failure()
    cb.record_failure()
    assert cb.get_state() == "CLOSED"
    cb.record_failure()
    assert cb.get_state() == "OPEN"


def test_circuit_breaker_half_open_then_close() -> None:
    from security.circuit_breaker import CircuitBreaker, CircuitState

    cb = CircuitBreaker(threshold=2, timeout=1)
    cb.record_failure()
    cb.record_failure()
    assert cb.get_state() == "OPEN"
    # Force timeout elapse
    cb._opened_at = time.monotonic() - 100
    assert cb.get_state() == "HALF-OPEN"
    cb.record_success()
    assert cb.get_state() == "CLOSED"
    assert cb._state == CircuitState.CLOSED


def test_policy_fallback_access() -> None:
    from security.policy import check_fallback_access

    assert check_fallback_access("admin", "POST") is True
    assert check_fallback_access("admin", "DELETE") is True
    assert check_fallback_access("user", "GET") is True
    assert check_fallback_access("user", "POST") is False
    assert check_fallback_access("unknown-role", "GET") is False


def test_policy_role_cache() -> None:
    from security.policy import clear_cache, get_cached_role, set_cached_role

    clear_cache()
    assert get_cached_role("uid-1") is None
    set_cached_role("uid-1", "admin")
    assert get_cached_role("uid-1") == "admin"


def test_policy_decode_jwt_role() -> None:
    from security.policy import decode_jwt_role

    token = jwt.encode({"sub": "u-7", "role": "admin"}, "sec", algorithm="HS256")
    user_id, role = decode_jwt_role(token, "sec")
    assert user_id == "u-7"
    assert role == "admin"


def test_policy_decode_jwt_role_defaults_to_user() -> None:
    from security.policy import decode_jwt_role

    token = jwt.encode({"sub": "u-9"}, "sec", algorithm="HS256")
    _, role = decode_jwt_role(token, "sec")
    assert role == "user"


def test_audit_log_decision_is_json() -> None:
    import io
    import json
    import logging

    from security.audit import JSONFormatter, log_decision

    # Capture audit logger output.
    logger = logging.getLogger("security.audit")
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    try:
        log_decision("u1", "admin", "GET", "/spaces", "allow", "ok", "CLOSED")
        handler.flush()
        line = buf.getvalue().strip().splitlines()[-1]
        payload = json.loads(line)
        assert payload["user_id"] == "u1"
        assert payload["decision"] == "allow"
        assert payload["circuit_breaker_state"] == "CLOSED"
    finally:
        logger.removeHandler(handler)


def test_sidecar_health_and_metrics() -> None:
    from fastapi.testclient import TestClient

    from security.main import app

    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert body["circuit_breaker"] in {"CLOSED", "HALF-OPEN", "OPEN"}

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert b"security_circuit_breaker_state" in metrics.content


def test_sidecar_open_state_denies_user_post() -> None:
    import importlib

    import security.main as sm
    from security.circuit_breaker import CircuitState

    importlib.reload(sm)
    sm.breaker._state = CircuitState.OPEN
    sm.breaker._opened_at = time.monotonic()

    from fastapi.testclient import TestClient

    client = TestClient(sm.app)
    # No token at all → 401
    assert client.get("/spaces").status_code == 401

    # User token → POST forbidden in fallback
    token = jwt.encode({"sub": "u1", "role": "user"}, sm.JWT_SECRET, algorithm="HS256")
    r = client.post("/spaces", cookies={"access_token": token})
    assert r.status_code == 403
