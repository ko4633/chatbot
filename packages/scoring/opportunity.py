"""Combines named sub-scores into the final Opportunity Score using
configurable weights. See docs/DATA_MODEL.md `opportunity.sub_scores` — the
per-component weight actually applied is stored alongside the score, not
just the final number, so the UI can render the full breakdown without
recomputing it.
"""

from __future__ import annotations

from dataclasses import dataclass

from packages.scoring.config_loader import load_opportunity_weights
from packages.scoring.sub_scores import SubScores


@dataclass(frozen=True)
class OpportunityScoreResult:
    score: float
    weights_version: str
    weighted_components: dict


def compute_opportunity_score(sub_scores: SubScores) -> OpportunityScoreResult:
    config = load_opportunity_weights()
    weights: dict[str, float] = config["weights"]
    scores = sub_scores.as_dict()

    weighted_components = {}
    total = 0.0
    for name, weight in weights.items():
        value = scores[name]
        contribution = value * weight
        weighted_components[name] = {
            "score": value,
            "weight": weight,
            "contribution": round(contribution, 2),
        }
        total += contribution

    return OpportunityScoreResult(
        score=round(total, 2),
        weights_version=config["version"],
        weighted_components=weighted_components,
    )
