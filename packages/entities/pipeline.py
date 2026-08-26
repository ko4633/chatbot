"""Orchestrates Stages 1-7 for a pair of variants, persists the EntityMatch,
and merges into a canonical Product on EXACT/LIKELY. See
docs/ARCHITECTURE.md §4 and docs/DATA_MODEL.md `entity_match`/`product`.
"""

from __future__ import annotations

import itertools
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from packages.ai.base import AIProvider
from packages.ai.errors import EmbeddingUnavailable
from packages.core.time_utils import utcnow
from packages.db.enums import ExtractionMethod, IdentifierType, MatchStage, MatchType
from packages.db.models.entity_match import EntityMatch
from packages.db.models.product import Product, ProductVariant
from packages.entities.stages import (
    attributes,
    embedding,
    fuzzy,
    identifier,
    llm_judge,
    string_match,
    vision,
)
from packages.entities.types import StageOutcome, StageResult, VariantView
from packages.observability.logging import get_logger

logger = get_logger(__name__)

ALGORITHM_VERSION = "entities.v1"
MERGE_CONFIDENCE_THRESHOLD = 0.6


def to_variant_view(v: ProductVariant) -> VariantView:
    return VariantView(
        id=v.id,
        title_raw=v.title_raw,
        title_language=v.title_language,
        brand_raw=v.brand_raw,
        identifier_type=v.identifier_type,
        identifier_value=v.identifier_value,
        model_number=v.model_number,
        dimensions_mm=v.dimensions_mm,
        weight_g=v.weight_g,
        capacity=v.capacity,
        material=v.material,
        color=v.color,
        pack_quantity=v.pack_quantity,
    )


@dataclass
class PairDecision:
    match_type: MatchType
    match_stage: MatchStage
    confidence: float
    evidence: dict
    ai_run_id: uuid.UUID | None = None


def evaluate_pair(
    db: Session,
    ai_provider: AIProvider,
    left: VariantView,
    right: VariantView,
    analysis_run_id: uuid.UUID | None,
) -> PairDecision:
    """Runs Stages 1-4 (pure, deterministic), then 5 (embedding, skip-on-
    unavailable), then 6 (vision, documented not-implemented), then 7 (LLM
    judge, skip-on-unavailable). Stops at the first stage that DECIDEs."""
    combined_evidence: dict = {}

    for stage_module in (identifier, attributes, string_match, fuzzy):
        result: StageResult = stage_module.run(left, right)
        combined_evidence[result.stage.value] = result.evidence
        if result.outcome == StageOutcome.DECIDED:
            assert result.match_type is not None  # invariant: DECIDED always sets match_type
            return PairDecision(
                result.match_type, result.stage, result.confidence, combined_evidence
            )

    try:
        emb_result = embedding.run(db, ai_provider, left, right, analysis_run_id)
        combined_evidence[emb_result.stage.value] = emb_result.evidence
        if emb_result.outcome == StageOutcome.DECIDED:
            assert emb_result.match_type is not None
            return PairDecision(
                emb_result.match_type, emb_result.stage, emb_result.confidence, combined_evidence
            )
    except EmbeddingUnavailable as e:
        combined_evidence[MatchStage.EMBEDDING.value] = {"skipped": True, "reason": str(e)}

    try:
        vision.run(left, right)
    except NotImplementedError as e:
        combined_evidence[MatchStage.VISION.value] = {"not_implemented": True, "reason": str(e)}

    llm_result = llm_judge.run(db, ai_provider, left, right, analysis_run_id)
    combined_evidence[llm_result.stage.value] = llm_result.evidence
    if llm_result.outcome == StageOutcome.DECIDED:
        assert llm_result.match_type is not None
        ai_run_id = None
        raw = llm_result.evidence.get("ai_run_id")
        if raw:
            ai_run_id = uuid.UUID(raw)
        return PairDecision(
            llm_result.match_type,
            llm_result.stage,
            llm_result.confidence,
            combined_evidence,
            ai_run_id,
        )

    return PairDecision(MatchType.UNKNOWN, MatchStage.LLM_JUDGE, 0.0, combined_evidence)


def _existing_match(db: Session, left_id: uuid.UUID, right_id: uuid.UUID) -> EntityMatch | None:
    return (
        db.query(EntityMatch)
        .filter(
            EntityMatch.algorithm_version == ALGORITHM_VERSION,
            (
                (
                    (EntityMatch.left_variant_id == left_id)
                    & (EntityMatch.right_variant_id == right_id)
                )
                | (
                    (EntityMatch.left_variant_id == right_id)
                    & (EntityMatch.right_variant_id == left_id)
                )
            ),
        )
        .first()
    )


def _merge_into_product(db: Session, left: ProductVariant, right: ProductVariant) -> uuid.UUID:
    existing = [pid for pid in (left.product_id, right.product_id) if pid is not None]
    unique_existing = set(existing)
    if len(unique_existing) > 1:
        logger.warning(
            "entity_match_merge_conflict",
            left_variant_id=str(left.id),
            right_variant_id=str(right.id),
            left_product_id=str(left.product_id),
            right_product_id=str(right.product_id),
        )
        return next(
            iter(unique_existing)
        )  # leave both as-is; do not cascade-merge two existing products
    if unique_existing:
        product_id = next(iter(unique_existing))
    else:
        primary_type = (
            left.identifier_type
            if left.identifier_type != IdentifierType.NONE
            else right.identifier_type
        )
        product = Product(
            canonical_title=left.title_raw if left.title_language == "ja" else right.title_raw,
            primary_identifier_type=primary_type,
            primary_identifier=left.identifier_value or right.identifier_value,
        )
        db.add(product)
        db.flush()
        product_id = product.id
    if left.product_id is None:
        left.product_id = product_id
    if right.product_id is None:
        right.product_id = product_id
    return product_id


@dataclass
class EntityResolutionStats:
    pairs_evaluated: int = 0
    pairs_skipped_existing: int = 0
    exact: int = 0
    likely: int = 0
    possible: int = 0
    rejected: int = 0
    unknown: int = 0
    products_created_or_merged: int = 0


def run_entity_resolution(
    db: Session, ai_provider: AIProvider, analysis_run_id: uuid.UUID | None = None
) -> EntityResolutionStats:
    stats = EntityResolutionStats()
    variants = db.query(ProductVariant).all()

    for left, right in itertools.combinations(variants, 2):
        if _existing_match(db, left.id, right.id) is not None:
            stats.pairs_skipped_existing += 1
            continue

        decision = evaluate_pair(
            db, ai_provider, to_variant_view(left), to_variant_view(right), analysis_run_id
        )
        stats.pairs_evaluated += 1

        resolved_product_id = None
        if (
            decision.match_type in (MatchType.EXACT, MatchType.LIKELY)
            and decision.confidence >= MERGE_CONFIDENCE_THRESHOLD
        ):
            resolved_product_id = _merge_into_product(db, left, right)
            stats.products_created_or_merged += 1

        computed_at = utcnow()
        match_row = EntityMatch(
            left_variant_id=left.id,
            right_variant_id=right.id,
            match_type=decision.match_type,
            match_stage=decision.match_stage,
            match_confidence=decision.confidence,
            evidence=decision.evidence,
            algorithm_version=ALGORITHM_VERSION,
            resolved_product_id=resolved_product_id,
            retrieved_at=computed_at,
            observed_at=computed_at,
            extraction_method=ExtractionMethod.DERIVED,
            confidence=decision.confidence,
            ai_run_id=decision.ai_run_id,
        )
        db.add(match_row)
        db.flush()

        if decision.match_type == MatchType.EXACT:
            stats.exact += 1
        elif decision.match_type == MatchType.LIKELY:
            stats.likely += 1
        elif decision.match_type == MatchType.POSSIBLE:
            stats.possible += 1
        elif decision.match_type == MatchType.REJECTED:
            stats.rejected += 1
        else:
            stats.unknown += 1

    return stats
