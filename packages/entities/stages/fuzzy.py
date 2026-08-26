"""Stage 4: fuzzy matching (edit-distance based) over normalized titles.

Same conservative rule as Stage 3: can only DECIDE LIKELY, never REJECT —
low fuzzy similarity across a ja/ko pair is uninformative, not evidence of a
mismatch.
"""

from __future__ import annotations

from rapidfuzz import fuzz

from packages.db.enums import MatchStage, MatchType
from packages.entities.types import StageResult, VariantView

STAGE = MatchStage.FUZZY
_RATIO_THRESHOLD = 85.0


def run(left: VariantView, right: VariantView) -> StageResult:
    score = fuzz.token_sort_ratio(left.title_raw, right.title_raw)
    if score >= _RATIO_THRESHOLD:
        return StageResult.decided(
            STAGE, MatchType.LIKELY, confidence=0.6, evidence={"fuzzy_ratio": round(score, 1)}
        )
    return StageResult.inconclusive(STAGE, {"fuzzy_ratio": round(score, 1)})
