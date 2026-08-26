"""Stage 7: LLM judge. Only reached when Stages 1-6 were all inconclusive.
Capped at LIKELY, never EXACT (ADR-0002) — see docs/AI_POLICY.md §5.

When AI is disabled, AIProvider.classify() returns label="UNKNOWN" with
ai_dependency=False (docs/AI_POLICY.md §6); this stage treats that as
INCONCLUSIVE, letting the pipeline's final fallback resolve to UNKNOWN
rather than fabricating a judgment.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from packages.ai.base import AIProvider
from packages.ai.types import ClassifyRequest
from packages.db.enums import AIRunPurpose, MatchStage, MatchType
from packages.entities.types import StageResult, VariantView

STAGE = MatchStage.LLM_JUDGE
PROMPT_VERSION = "llm_judge.v1"
_LABELS = ["SAME_PRODUCT", "DIFFERENT_PRODUCT"]


def _describe(v: VariantView) -> str:
    return (
        f"title={v.title_raw!r} language={v.title_language} brand={v.brand_raw!r} "
        f"model_number={v.model_number!r} identifier={v.identifier_type.value}:{v.identifier_value!r} "
        f"dimensions_mm={v.dimensions_mm} weight_g={v.weight_g} capacity={v.capacity!r} "
        f"material={v.material!r} color={v.color!r} pack_quantity={v.pack_quantity}"
    )


def run(
    db: Session,
    ai_provider: AIProvider,
    left: VariantView,
    right: VariantView,
    analysis_run_id: uuid.UUID | None,
) -> StageResult:
    text = (
        "Two product listings, possibly from different countries/languages. "
        "Deterministic checks (shared identifier, model number, dimensions, string/fuzzy "
        "similarity) were all inconclusive. Judge whether they describe the same physical "
        f"product.\n\nListing A: {_describe(left)}\n\nListing B: {_describe(right)}"
    )
    result = ai_provider.classify(
        db,
        ClassifyRequest(
            purpose=AIRunPurpose.ENTITY_MATCH_JUDGE,
            text=text,
            labels=_LABELS,
            prompt_version=PROMPT_VERSION,
            model_tier="premium",
            analysis_run_id=analysis_run_id,
        ),
    )
    if not result.ai_dependency or result.label == "UNKNOWN":
        return StageResult.inconclusive(
            STAGE, {"ai_dependency": result.ai_dependency, "label": result.label}
        )
    if result.label == "SAME_PRODUCT":
        return StageResult.decided(
            STAGE,
            MatchType.LIKELY,
            confidence=0.7,
            evidence={"label": result.label, "ai_run_id": str(result.ai_run_id)},
        )
    return StageResult.decided(
        STAGE,
        MatchType.REJECTED,
        confidence=0.7,
        evidence={"label": result.label, "ai_run_id": str(result.ai_run_id)},
    )
