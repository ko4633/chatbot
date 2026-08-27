"""Structured logging setup.

Tracks request_id / correlation_id / job_id / analysis_run_id / ai_run_id
per docs/MASTER_SPEC.md §36 by binding them into structlog's contextvars,
so any log line emitted anywhere during a request/job carries them without
threading extra parameters through every function call.
"""

from __future__ import annotations

import logging
import sys

import structlog

from packages.observability.redact import redact_event


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            redact_event,  # type: ignore[list-item]  # structlog's Processor stub is stricter than the real runtime contract
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


def bind_context(**kwargs: object) -> None:
    """Bind ids (request_id, analysis_run_id, ai_run_id, job_id, ...) for this context."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    structlog.contextvars.clear_contextvars()
