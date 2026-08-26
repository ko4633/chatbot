"""Retry with exponential backoff for collector fetches. See
docs/ARCHITECTURE.md §6 (Adversarial Review: Collector failure isolation).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from packages.observability.logging import get_logger

logger = get_logger(__name__)
T = TypeVar("T")


def retry_with_backoff(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay_seconds: float = 0.5,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except retryable_exceptions as e:  # noqa: PERF203 - retry loop, not a hot path
            last_error = e
            logger.warning(
                "collector_attempt_failed", attempt=attempt, max_attempts=max_attempts, error=str(e)
            )
            if attempt < max_attempts:
                time.sleep(base_delay_seconds * (2 ** (attempt - 1)))
    assert last_error is not None
    raise last_error
