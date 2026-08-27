"""Stage 5: embedding similarity. Only reachable when an embeddings provider
is actually configured — see docs/AI_POLICY.md §6 and ADR-0005. Raises
EmbeddingUnavailable (propagated from AIProvider.embed) when it is not;
packages/entities/pipeline.py treats that as "stage skipped", never as a
mismatch.

Like Stages 3/4, this stage can only DECIDE a LIKELY match on high
similarity. Low similarity is not strong enough on its own to REJECT —
translation/phrasing differences can suppress similarity for a true match —
so low-similarity falls through as INCONCLUSIVE.
"""

from __future__ import annotations

import math
import uuid

from sqlalchemy.orm import Session

from packages.ai.base import AIProvider
from packages.ai.types import EmbedRequest
from packages.db.enums import AIRunPurpose, MatchStage, MatchType
from packages.entities.types import StageResult, VariantView

STAGE = MatchStage.EMBEDDING
PROMPT_VERSION = "embedding.v1"
_SIMILARITY_THRESHOLD = 0.85


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def run(
    db: Session,
    ai_provider: AIProvider,
    left: VariantView,
    right: VariantView,
    analysis_run_id: uuid.UUID | None,
) -> StageResult:
    left_vec = ai_provider.embed(
        db,
        EmbedRequest(
            purpose=AIRunPurpose.EMBEDDING,
            text=left.title_raw,
            prompt_version=PROMPT_VERSION,
            analysis_run_id=analysis_run_id,
        ),
    ).vector
    right_vec = ai_provider.embed(
        db,
        EmbedRequest(
            purpose=AIRunPurpose.EMBEDDING,
            text=right.title_raw,
            prompt_version=PROMPT_VERSION,
            analysis_run_id=analysis_run_id,
        ),
    ).vector
    similarity = _cosine_similarity(left_vec, right_vec)
    if similarity >= _SIMILARITY_THRESHOLD:
        return StageResult.decided(
            STAGE,
            MatchType.LIKELY,
            confidence=0.7,
            evidence={"cosine_similarity": round(similarity, 4)},
        )
    return StageResult.inconclusive(STAGE, {"cosine_similarity": round(similarity, 4)})
