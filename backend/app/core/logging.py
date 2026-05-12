"""Structured logging configuration for Draftwell.

Call configure_logging() once at app startup. All modules should use
logging.getLogger(__name__) — never print().
"""

from __future__ import annotations

import logging
import sys

_STANDARD_LOGRECORD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname",
    "filename", "module", "exc_info", "exc_text", "stack_info",
    "lineno", "funcName", "created", "msecs", "relativeCreated",
    "thread", "threadName", "processName", "process", "message",
    "asctime", "taskName",
}


def configure_logging(level: int = logging.INFO) -> None:
    """Wire up a structured key=value handler on the root logger."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_KeyValueFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
    logging.getLogger("httpx").setLevel(logging.WARNING)


class _KeyValueFormatter(logging.Formatter):
    """Emits log records as space-separated key=value pairs for easy grepping."""

    def format(self, record: logging.LogRecord) -> str:
        base = f"level={record.levelname} logger={record.name} msg={record.getMessage()!r}"
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _STANDARD_LOGRECORD_ATTRS and not k.startswith("_")
        }
        if extras:
            pairs = " ".join(f"{k}={v!r}" for k, v in extras.items())
            return f"{base} {pairs}"
        return base
