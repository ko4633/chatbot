"""Entity-resolution evaluation against the golden dataset
(docs/EVALUATION.md §2). Runnable standalone (`python -m tests.evals.eval_entity_resolution`)
or imported by tests/evals/test_golden_entity_matches.py for the CI gate.

Does not require AI: every golden-dataset pair is designed to resolve via
deterministic Stages 1-4 (see tests/fixtures/golden_entity_matches.yaml
notes), so this eval runs the same with or without an API key configured.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from packages.ai.null_provider import NullAIProvider
from packages.collectors.japan_marketplace import JapanMarketplaceProvider
from packages.collectors.korea_marketplace import KoreaMarketplaceProvider
from packages.collectors.runner import run_collector
from packages.collectors.storage import LocalFileStore
from packages.db.enums import MatchType
from packages.db.models.offer import Offer
from packages.db.models.product import ProductVariant
from packages.entities.pipeline import evaluate_pair, to_variant_view

GOLDEN_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "golden_entity_matches.yaml"

# A predicted match_type counts as a "positive" (system asserts sameness).
POSITIVE_MATCH_TYPES = {MatchType.EXACT, MatchType.LIKELY}

LABEL_EXPECTS_POSITIVE = {
    "SAME_PRODUCT": True,
    "VARIANT": False,
    "DIFFERENT_PRODUCT": False,
    "UNKNOWN": False,
}


@dataclass
class EvalResult:
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    total_pairs: int
    details: list[dict]


def _variant_for_listing_url(db: Session, listing_url: str) -> ProductVariant:
    offer = db.query(Offer).filter_by(listing_url=listing_url).one()
    variant = db.get(ProductVariant, offer.product_variant_id)
    assert variant is not None
    return variant


def run_eval(db: Session, tmp_path: str) -> EvalResult:
    store = LocalFileStore(tmp_path)
    run_collector(db, JapanMarketplaceProvider(), store)
    run_collector(db, KoreaMarketplaceProvider(), store)
    db.commit()

    golden = yaml.safe_load(GOLDEN_PATH.read_text())["pairs"]
    ai_provider = NullAIProvider()

    true_positives = false_positives = false_negatives = true_negatives = 0
    details = []

    for case in golden:
        left = to_variant_view(_variant_for_listing_url(db, case["left"]))
        right = to_variant_view(_variant_for_listing_url(db, case["right"]))
        decision = evaluate_pair(db, ai_provider, left, right, analysis_run_id=None)

        predicted_positive = decision.match_type in POSITIVE_MATCH_TYPES
        expected_positive = LABEL_EXPECTS_POSITIVE[case["label"]]

        if predicted_positive and expected_positive:
            true_positives += 1
        elif predicted_positive and not expected_positive:
            false_positives += 1
        elif not predicted_positive and expected_positive:
            false_negatives += 1
        else:
            true_negatives += 1

        details.append(
            {
                "left": case["left"],
                "right": case["right"],
                "label": case["label"],
                "predicted_match_type": decision.match_type.value,
                "correct": predicted_positive == expected_positive,
            }
        )

    total_positive_predictions = true_positives + false_positives
    total_actual_positives = true_positives + false_negatives

    precision = true_positives / total_positive_predictions if total_positive_predictions else 1.0
    recall = true_positives / total_actual_positives if total_actual_positives else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    false_positive_rate = (
        false_positives / total_positive_predictions if total_positive_predictions else 0.0
    )

    return EvalResult(
        precision=precision,
        recall=recall,
        f1=f1,
        false_positive_rate=false_positive_rate,
        total_pairs=len(golden),
        details=details,
    )


if __name__ == "__main__":
    import sys
    import tempfile

    from packages.db.base import get_session_factory

    session = get_session_factory()()
    with tempfile.TemporaryDirectory() as tmp:
        result = run_eval(session, tmp)
    print(
        f"precision={result.precision:.3f} recall={result.recall:.3f} f1={result.f1:.3f} "
        f"false_positive_rate={result.false_positive_rate:.3f}"
    )
    for d in result.details:
        marker = "OK" if d["correct"] else "FAIL"
        print(
            f"  [{marker}] {d['label']:18} predicted={d['predicted_match_type']:10} {d['left']} <-> {d['right']}"
        )
    sys.exit(0 if result.false_positive_rate == 0 else 1)
