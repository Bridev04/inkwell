"""Structured logging configuration for Draftwell.

Call configure_logging() once at app startup. All modules should use
logging.getLogger(__name__) — never print().
"""

from __future__ import annotations

import logging
import sys

# Keys that must never appear in structured log output.
# If a caller accidentally passes one of these as an extra, the value is
# replaced with [REDACTED] so secrets cannot leak through log aggregators.
_SENSITIVE_EXTRA_KEYS = frozenset(
    {
        "token",
        "access_token",
        "password",
        "secret",
        "api_key",
        "authorization",
        "cookie",
        "jwt",
        "hashed_password",
    }
)

_STANDARD_LOGRECORD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
    "taskName",
}


def configure_logging(level: int = logging.INFO) -> None:
    """Wire up a structured key=value handler on the root logger."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_KeyValueFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
    logging.getLogger("httpx").setLevel(logging.WARNING)


class _KeyValueFormatter(logging.Formatter):
    """Emits log records as space-separated key=value pairs for easy grepping.

    Any extra field whose name matches _SENSITIVE_EXTRA_KEYS is replaced with
    [REDACTED] so secrets cannot leak through log aggregators.
    """

    def format(self, record: logging.LogRecord) -> str:
        base = f"level={record.levelname} logger={record.name} msg={record.getMessage()!r}"
        extras = {
            k: ("[REDACTED]" if k.lower() in _SENSITIVE_EXTRA_KEYS else v)
            for k, v in record.__dict__.items()
            if k not in _STANDARD_LOGRECORD_ATTRS and not k.startswith("_")
        }
        if extras:
            pairs = " ".join(f"{k}={v!r}" for k, v in extras.items())
            return f"{base} {pairs}"
        return base
