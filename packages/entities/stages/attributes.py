"""Stage 2: deterministic attributes (model number, dimensions, weight,
capacity, pack quantity). Capped at LIKELY, never EXACT (ADR-0002).

model_number is treated as the primary signal because it is typically
written identically regardless of listing language (e.g. "JNL-450" appears
unchanged in both a Japanese and a Korean listing), unlike brand strings
(see docs/entities/normalize.py normalize_brand docstring for why brand
equality is not required here).
"""

from __future__ import annotations

from packages.db.enums import MatchStage, MatchType
from packages.entities.normalize import normalize_token
from packages.entities.types import StageResult, VariantView

STAGE = MatchStage.ATTRIBUTES

_DIM_TOLERANCE_MM = 3
_WEIGHT_TOLERANCE_RATIO = 0.05


def _dims_close(a: dict | None, b: dict | None) -> bool:
    if not a or not b:
        return False
    for key in ("l", "w", "h"):
        if key not in a or key not in b:
            return False
        if abs(a[key] - b[key]) > _DIM_TOLERANCE_MM:
            return False
    return True


def _weight_close(a: int | None, b: int | None) -> bool:
    if a is None or b is None:
        return False
    if a == 0 or b == 0:
        return a == b
    return abs(a - b) / max(a, b) <= _WEIGHT_TOLERANCE_RATIO


def run(left: VariantView, right: VariantView) -> StageResult:
    if left.model_number and right.model_number:
        left_model = normalize_token(left.model_number)
        right_model = normalize_token(right.model_number)
        if left_model == right_model:
            return StageResult.decided(
                STAGE,
                MatchType.LIKELY,
                confidence=0.9,
                evidence={"signal": "model_number_equal", "model_number": left_model},
            )
        return StageResult.decided(
            STAGE,
            MatchType.REJECTED,
            confidence=0.9,
            evidence={
                "signal": "model_number_mismatch",
                "left_model_number": left_model,
                "right_model_number": right_model,
            },
        )

    # No model number on at least one side: fall back to dimensions + weight
    # as a corroborating deterministic signal. This is weaker than a model
    # number match (lower confidence) — many unrelated products share
    # similar dimensions, so this alone is not conclusive on its own.
    if _dims_close(left.dimensions_mm, right.dimensions_mm) and _weight_close(
        left.weight_g, right.weight_g
    ):
        return StageResult.decided(
            STAGE,
            MatchType.LIKELY,
            confidence=0.65,
            evidence={
                "signal": "dimensions_and_weight_close",
                "left_dimensions_mm": left.dimensions_mm,
                "right_dimensions_mm": right.dimensions_mm,
                "left_weight_g": left.weight_g,
                "right_weight_g": right.weight_g,
            },
        )

    return StageResult.inconclusive(
        STAGE, {"reason": "no model_number on one/both sides and dimensions/weight not both close"}
    )
