"""CI gate wrapper around tests/evals/eval_entity_resolution.py. Per
docs/EVALUATION.md §2: false_positive_rate == 0 is required to merge;
recall/precision/F1 are reported but not blocking given the golden set's
small, hand-curated size.
"""

from __future__ import annotations

from tests.evals.eval_entity_resolution import run_eval


def test_golden_dataset_has_zero_false_positives(clean_db, tmp_path):
    result = run_eval(clean_db, str(tmp_path / "raw"))
    failures = [d for d in result.details if not d["correct"]]
    assert result.false_positive_rate == 0.0, f"false positives found: {failures}"


def test_golden_dataset_recall_and_f1_reported(clean_db, tmp_path):
    result = run_eval(clean_db, str(tmp_path / "raw"))
    # Not a hard gate (small hand-curated set per docs/EVALUATION.md §2), but
    # a collapse to 0 recall would mean deterministic matching stopped
    # working entirely — that IS worth failing loudly on.
    assert result.recall > 0.0
    assert result.total_pairs == 7
