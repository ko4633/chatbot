"""Pure, DB-independent types for entity resolution. Keeping stage functions
free of SQLAlchemy makes them directly unit-testable (docs/EVALUATION.md §3)
without a database."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from packages.db.enums import IdentifierType, MatchStage, MatchType


class StageOutcome(StrEnum):
    INCONCLUSIVE = "INCONCLUSIVE"  # fall through to the next stage
    DECIDED = "DECIDED"  # this stage produced a final answer; stop the pipeline


@dataclass(frozen=True)
class VariantView:
    """The comparable fields of a ProductVariant, independent of the ORM."""

    id: uuid.UUID
    title_raw: str
    title_language: str
    brand_raw: str | None
    identifier_type: IdentifierType
    identifier_value: str | None
    model_number: str | None
    dimensions_mm: dict | None
    weight_g: int | None
    capacity: str | None
    material: str | None
    color: str | None
    pack_quantity: int | None


@dataclass(frozen=True)
class StageResult:
    outcome: StageOutcome
    stage: MatchStage
    match_type: MatchType | None = None  # set only when outcome == DECIDED
    confidence: float = 0.0
    evidence: dict = field(default_factory=dict)

    @staticmethod
    def inconclusive(stage: MatchStage, evidence: dict | None = None) -> StageResult:
        return StageResult(outcome=StageOutcome.INCONCLUSIVE, stage=stage, evidence=evidence or {})

    @staticmethod
    def decided(
        stage: MatchStage, match_type: MatchType, confidence: float, evidence: dict
    ) -> StageResult:
        return StageResult(
            outcome=StageOutcome.DECIDED,
            stage=stage,
            match_type=match_type,
            confidence=confidence,
            evidence=evidence,
        )
