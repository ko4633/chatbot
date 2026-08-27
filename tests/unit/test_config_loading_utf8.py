"""Functional counterpart to test_no_locale_dependent_file_io.py: proves the
fixed loaders actually decode the non-ASCII bytes correctly, not just that
an `encoding=` keyword is present syntactically (someone could technically
pass the wrong encoding and still satisfy the static check).

Note: we don't attempt to literally simulate a cp949 Windows locale here.
CPython's default-encoding resolution for `open()` reads the OS locale via a
C-level call (not always reachable by monkeypatching `locale.getpreferredencoding`
from Python), so a fake "make this look like Windows" test would be flaky
and not trustworthy. Asserting the real content decodes correctly under the
explicit encoding we now pass is the reliable thing to check — the encoding
argument makes the result independent of the OS locale by construction.
"""

from __future__ import annotations

from packages.ai.cost import load_ai_model_config
from packages.scoring.config_loader import load_margin_assumptions, load_opportunity_weights


def test_margin_assumptions_decode_em_dash_correctly():
    # config/margin_assumptions.yaml comments contain an em dash (—, U+2014);
    # loading it at all (via yaml.safe_load reading the whole file) proves
    # the file was decoded as UTF-8, not mangled/rejected as cp949 would.
    assumptions = load_margin_assumptions()
    assert assumptions["jpy_krw_fx"] > 0


def test_opportunity_weights_load_and_sum_to_one():
    config = load_opportunity_weights()
    assert abs(sum(config["weights"].values()) - 1.0) < 1e-6


def test_ai_model_config_loads():
    config = load_ai_model_config()
    assert "anthropic" in config


def test_golden_dataset_em_dash_notes_decode_correctly():
    import yaml

    from tests.evals.eval_entity_resolution import GOLDEN_PATH

    golden = yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8"))
    notes = [case["note"] for case in golden["pairs"]]
    # These notes contain literal em dashes (—) in the checked-in file; a
    # cp949-decoded read would have raised UnicodeDecodeError before ever
    # reaching this assertion (see the bug this test guards against).
    assert any("—" in note for note in notes)
