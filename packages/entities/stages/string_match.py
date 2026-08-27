"""Stage 3: normalized string matching (token overlap).

Deliberately conservative: this stage can only DECIDE a LIKELY match on
strong lexical overlap. It never REJECTS — a real match can legitimately
share zero tokens across a Japanese/Korean title pair (that's exactly why
Stages 5/7 exist), so the absence of lexical overlap is evidence of nothing
and must fall through as INCONCLUSIVE, not be treated as a mismatch.
"""

from __future__ import annotations

from packages.db.enums import MatchStage, MatchType
from packages.entities.normalize import tokenize_title
from packages.entities.types import StageResult, VariantView

STAGE = MatchStage.STRING
_JACCARD_THRESHOLD = 0.5
_MIN_SHARED_TOKENS = 1


def run(left: VariantView, right: VariantView) -> StageResult:
    left_tokens = tokenize_title(left.title_raw)
    right_tokens = tokenize_title(right.title_raw)
    shared = left_tokens & right_tokens
    union = left_tokens | right_tokens
    jaccard = len(shared) / len(union) if union else 0.0

    if len(shared) >= _MIN_SHARED_TOKENS and jaccard >= _JACCARD_THRESHOLD:
        return StageResult.decided(
            STAGE,
            MatchType.LIKELY,
            confidence=0.6,
            evidence={"jaccard": round(jaccard, 3), "shared_tokens": sorted(shared)},
        )
    return StageResult.inconclusive(
        STAGE, {"jaccard": round(jaccard, 3), "shared_tokens": sorted(shared)}
    )
