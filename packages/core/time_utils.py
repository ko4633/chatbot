"""Time utilities. All timestamps in OMNIS are timezone-aware UTC.

Date/time arithmetic is deterministic code, never delegated to AI
(docs/AI_POLICY.md §3).
"""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)
