"""Stage 1: exact identifier. See docs/AI_POLICY.md §5 and ADR-0002 — this
is the ONLY stage allowed to produce MatchType.EXACT."""

from __future__ import annotations

from packages.db.enums import IdentifierType, MatchStage, MatchType
from packages.entities.normalize import normalize_token
from packages.entities.types import StageResult, VariantView

STAGE = MatchStage.IDENTIFIER


def run(left: VariantView, right: VariantView) -> StageResult:
    if left.identifier_type == IdentifierType.NONE or right.identifier_type == IdentifierType.NONE:
        return StageResult.inconclusive(STAGE, {"reason": "one or both sides have no identifier"})
    if left.identifier_type != right.identifier_type:
        return StageResult.inconclusive(
            STAGE,
            {
                "reason": "different identifier types, not directly comparable",
                "left_type": left.identifier_type.value,
                "right_type": right.identifier_type.value,
            },
        )
    left_val = normalize_token(left.identifier_value or "")
    right_val = normalize_token(right.identifier_value or "")
    if not left_val or not right_val:
        return StageResult.inconclusive(STAGE, {"reason": "empty identifier value"})
    if left_val == right_val:
        return StageResult.decided(
            STAGE,
            MatchType.EXACT,
            confidence=1.0,
            evidence={"identifier_type": left.identifier_type.value, "value": left_val},
        )
    return StageResult.decided(
        STAGE,
        MatchType.REJECTED,
        confidence=1.0,
        evidence={
            "reason": "same identifier type, different values",
            "identifier_type": left.identifier_type.value,
            "left_value": left_val,
            "right_value": right_val,
        },
    )
