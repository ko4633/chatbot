"""Stage 6: image/vision similarity. NOT IMPLEMENTED in Phase 1 — there is no
image pipeline (no image fetch/storage, no vision model integration). This
module exists only as the documented interface placeholder required by
docs/MASTER_SPEC.md §8. It always raises NotImplementedError; the pipeline
calls it specifically so that fact is verified rather than assumed, and
records "NOT_IMPLEMENTED" (not "SKIPPED") in evidence — see
docs/ARCHITECTURE.md §4: a stage that was never attempted must not be
recorded the same way as a stage that was attempted and unavailable.
"""

from __future__ import annotations

from packages.entities.types import VariantView


def run(left: VariantView, right: VariantView) -> None:
    raise NotImplementedError(
        "Stage 6 (vision similarity) has no image pipeline in Phase 1 — LIVE_CONNECTOR_PENDING"
    )
