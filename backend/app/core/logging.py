"""Structured logging configuration for Inkwell.

Call configure_logging() once at app startup. All modules should use
logging.getLogger(__name__) — never print().
"""

from __future__ import annotations

import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    """Wire up a JSON-style structured handler on the root logger."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_KeyValueFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)


class _KeyValueFormatter(logging.Formatter):
    """Emits log records as space-separated key=value pairs for easy grepping."""

    def format(self, record: logging.LogRecord) -> str:
        base = f"level={record.levelname} logger={record.name} msg={record.getMessage()!r}"
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in logging.LogRecord.__dict__
            and not k.startswith("_")
            and k
            not in {
                "message",
                "asctime",
                "args",
                "exc_info",
                "exc_text",
                "stack_info",
                "taskName",
            }
        }
        if extras:
            pairs = " ".join(f"{k}={v!r}" for k, v in extras.items())
            return f"{base} {pairs}"
        return base
