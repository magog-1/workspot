"""Thread-safe Circuit Breaker with CLOSED / OPEN / HALF-OPEN states."""

from __future__ import annotations

import threading
import time
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF-OPEN"


class CircuitBreaker:
    """Simple circuit breaker.

    - CLOSED: requests pass through, failures are counted.
    - OPEN: requests short-circuit. After ``timeout`` seconds the breaker
      transitions to HALF-OPEN on the next ``get_state()`` call.
    - HALF-OPEN: a single probe request is allowed; success → CLOSED,
      failure → OPEN.
    """

    def __init__(self, threshold: int = 5, timeout: int = 60) -> None:
        self.threshold = threshold
        self.timeout = timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    def record_failure(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                return
            self._failure_count += 1
            if self._failure_count >= self.threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()

    def record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._opened_at = None
                return
            self._failure_count = 0

    def get_state(self) -> str:
        with self._lock:
            if (
                self._state == CircuitState.OPEN
                and self._opened_at is not None
                and (time.monotonic() - self._opened_at) >= self.timeout
            ):
                self._state = CircuitState.HALF_OPEN
            return self._state.value

    def reset(self) -> None:
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._opened_at = None
