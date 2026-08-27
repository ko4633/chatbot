"""Deterministic collector data-quality assessment — catches a collector
that returned 200 OK but garbage/degraded data (product brief §16), never an
LLM judgment call. See docs/DATA_MODEL.md `source.data_quality_status`.

Phase 2 scope: yield-drop detection only (this run's items_succeeded vs the
previous run's, for the same collector). Content-level anomalies (e.g. this
run's average price is wildly different from history) are NOT implemented
yet — flagged honestly in the Phase 2 build report rather than faked.
"""

from __future__ import annotations

from packages.collectors.runner import CollectorRunStats
from packages.db.enums import DataQualityStatus

# A run that succeeds on fewer than this fraction of the items a *previous*
# successful run saw is DEGRADED — a real drop in yield, not necessarily a
# crash.
YIELD_DROP_DEGRADED_THRESHOLD = 0.5


def effective_yield_from_stats(stats: dict) -> int:
    """Same effective-yield definition, applied to a stored
    AnalysisRun.stats["collectors"][source_name] dict instead of a live
    CollectorRunStats — used to look up the previous run's yield."""
    return _effective_yield(
        stats.get("items_succeeded", 0), stats.get("items_skipped_duplicate", 0)
    )


def _effective_yield(items_succeeded: int, items_skipped_duplicate: int) -> int:
    """A duplicate-skip is idempotency working as designed (the item was
    already ingested by an earlier run), not a failure to collect it — so it
    counts toward yield the same as a fresh success. Comparing raw
    items_succeeded run-over-run would wrongly flag every already-fully-
    ingested re-run as FAILED once nothing is new."""
    return items_succeeded + items_skipped_duplicate


def assess_collector_run(
    current: CollectorRunStats, previous_effective_yield: int | None
) -> DataQualityStatus:
    """Never QUARANTINED here — that status is reserved for a deliberate
    operator override (docs/DATA_MODEL.md), not something this function
    infers on its own."""
    effective_yield = _effective_yield(current.items_succeeded, current.items_skipped_duplicate)
    if current.items_seen > 0 and effective_yield == 0:
        return DataQualityStatus.FAILED
    if previous_effective_yield is not None and previous_effective_yield > 0:
        yield_ratio = effective_yield / previous_effective_yield
        if yield_ratio < YIELD_DROP_DEGRADED_THRESHOLD:
            return DataQualityStatus.DEGRADED
    return DataQualityStatus.HEALTHY
