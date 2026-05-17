"""JSON-formatted audit logging for security decisions."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "user_id": getattr(record, "user_id", None),
                "user_role": getattr(record, "user_role", None),
                "action": getattr(record, "action", None),
                "resource": getattr(record, "resource", None),
                "decision": getattr(record, "decision", None),
                "reason": getattr(record, "reason", None),
                "circuit_breaker_state": getattr(record, "cb_state", None),
            }
        )


_logger: logging.Logger | None = None


def get_audit_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger
    logger = logging.getLogger("security.audit")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    _logger = logger
    return logger


def log_decision(
    user_id: str | None,
    role: str | None,
    action: str,
    resource: str,
    decision: str,
    reason: str,
    cb_state: str,
) -> None:
    logger = get_audit_logger()
    logger.info(
        "decision",
        extra={
            "user_id": user_id,
            "user_role": role,
            "action": action,
            "resource": resource,
            "decision": decision,
            "reason": reason,
            "cb_state": cb_state,
        },
    )
