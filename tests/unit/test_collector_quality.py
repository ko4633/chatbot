"""Deterministic collector data-quality assessment (docs/MASTER_SPEC.md §16).
A duplicate-skip on a re-run counts as yield, same as a fresh success — the
bug this specifically guards against is a fully-idempotent re-run (nothing
new to ingest, everything skipped as duplicate) being wrongly flagged FAILED
just because items_succeeded alone reads 0.
"""

from __future__ import annotations

from packages.collectors.quality import (
    assess_collector_run,
    effective_yield_from_stats,
)
from packages.collectors.runner import CollectorRunStats
from packages.db.enums import DataQualityStatus


def _stats(seen=10, succeeded=10, failed=0, skipped_duplicate=0) -> CollectorRunStats:
    return CollectorRunStats(
        items_seen=seen,
        items_succeeded=succeeded,
        items_failed=failed,
        items_skipped_duplicate=skipped_duplicate,
        observations_written=succeeded * 3,
    )


def test_no_previous_run_and_full_success_is_healthy():
    result = assess_collector_run(_stats(), previous_effective_yield=None)
    assert result == DataQualityStatus.HEALTHY


def test_zero_effective_yield_with_items_seen_is_failed():
    result = assess_collector_run(_stats(seen=10, succeeded=0, skipped_duplicate=0), previous_effective_yield=None)
    assert result == DataQualityStatus.FAILED


def test_fully_idempotent_rerun_with_zero_new_successes_is_not_failed():
    # Everything already ingested -> items_succeeded=0, but all skipped as
    # duplicate, not failed. Must not be flagged FAILED or DEGRADED.
    current = _stats(seen=10, succeeded=0, skipped_duplicate=10)
    result = assess_collector_run(current, previous_effective_yield=10)
    assert result == DataQualityStatus.HEALTHY


def test_significant_yield_drop_is_degraded():
    current = _stats(seen=10, succeeded=2, skipped_duplicate=0)
    result = assess_collector_run(current, previous_effective_yield=10)
    assert result == DataQualityStatus.DEGRADED


def test_minor_yield_drop_is_still_healthy():
    current = _stats(seen=10, succeeded=8, skipped_duplicate=0)
    result = assess_collector_run(current, previous_effective_yield=10)
    assert result == DataQualityStatus.HEALTHY


def test_effective_yield_from_stats_sums_succeeded_and_skipped_duplicate():
    assert effective_yield_from_stats({"items_succeeded": 3, "items_skipped_duplicate": 4}) == 7
    assert effective_yield_from_stats({}) == 0
