"""Full ingest -> entity resolution -> scoring -> opportunity pipeline,
against the bundled JP/KR demo fixtures. Also proves the system boots and
runs completely with AI disabled (docs/AI_POLICY.md §6) since NullAIProvider
is used throughout.
"""

from __future__ import annotations

from packages.ai.null_provider import NullAIProvider
from packages.collectors.japan_marketplace import JapanMarketplaceProvider
from packages.collectors.korea_marketplace import KoreaMarketplaceProvider
from packages.collectors.storage import LocalFileStore
from packages.db.enums import AnalysisRunStatus
from packages.db.models.opportunity import Opportunity
from packages.db.models.product import Product
from packages.intelligence.pipeline import run_full_analysis


def _run_pipeline(db, tmp_path):
    store = LocalFileStore(str(tmp_path / "raw"))
    return run_full_analysis(
        db,
        NullAIProvider(),
        [JapanMarketplaceProvider(), KoreaMarketplaceProvider()],
        store,
        triggered_by="pytest",
    )


def test_pipeline_runs_end_to_end_with_ai_disabled(clean_db, tmp_path):
    run = _run_pipeline(clean_db, tmp_path)
    assert run.status in (AnalysisRunStatus.SUCCEEDED, AnalysisRunStatus.PARTIAL)
    assert run.stats["entity_resolution"]["exact"] >= 4  # OLFA 43B (JP+2 KR) and L-type (JP+KR)


def test_pipeline_creates_exactly_the_expected_opportunities(clean_db, tmp_path):
    _run_pipeline(clean_db, tmp_path)
    opportunities = clean_db.query(Opportunity).all()
    titles = {clean_db.get(Product, o.product_id).canonical_title for o in opportunities}
    # The two THERMOS bottle families and the two OLFA knives all resolve
    # cross-market; the ambiguous kitchen-scissors pair must NOT (see
    # tests/evals/eval_entity_resolution.py + golden dataset).
    assert len(opportunities) == 4
    assert not any("キッチンバサミ" in t or "주방가위" in t for t in titles)


def test_negative_margin_opportunity_scores_lower_than_positive_margin_one(clean_db, tmp_path):
    _run_pipeline(clean_db, tmp_path)
    opportunities = {
        clean_db.get(Product, o.product_id).canonical_title: o
        for o in clean_db.query(Opportunity).all()
    }
    olfa_knife = next(o for t, o in opportunities.items() if "別たち" in t)
    thermos_450 = next(o for t, o in opportunities.items() if "JNL-450" in t)

    assert float(olfa_knife.economics["contribution_margin_krw"]) < 0
    assert float(thermos_450.economics["contribution_margin_krw"]) > 0
    # A price drop event exists for the knife, but bad unit economics must
    # still pull its score below a genuinely profitable opportunity —
    # exactly the "why the eye-catching signal isn't enough" case this
    # system exists to catch (docs/MASTER_SPEC.md §0/§58).
    assert float(olfa_knife.opportunity_score) < float(thermos_450.opportunity_score)


def test_confidence_score_is_independent_of_opportunity_score(clean_db, tmp_path):
    """ADR-0003: a LIKELY (attribute-matched) product can carry a lower
    confidence than an EXACT (identifier-matched) one regardless of which
    one scores higher on opportunity — the two numbers must not move
    together mechanically."""
    _run_pipeline(clean_db, tmp_path)
    opportunities = {
        clean_db.get(Product, o.product_id).canonical_title: o
        for o in clean_db.query(Opportunity).all()
    }
    olfa_knife = next(o for t, o in opportunities.items() if "別たち" in t)  # EXACT match
    thermos_450 = next(o for t, o in opportunities.items() if "JNL-450" in t)  # LIKELY match

    assert float(olfa_knife.confidence_score) > float(thermos_450.confidence_score)
    assert float(olfa_knife.opportunity_score) < float(thermos_450.opportunity_score)


def test_rerunning_pipeline_marks_previous_opportunity_stale(clean_db, tmp_path):
    from packages.db.enums import OpportunityStatus

    run1 = _run_pipeline(clean_db, tmp_path)
    first_ids = {o.id for o in clean_db.query(Opportunity).filter_by(analysis_run_id=run1.id).all()}

    run2 = _run_pipeline(clean_db, tmp_path)
    assert run2.id != run1.id

    stale = clean_db.query(Opportunity).filter(Opportunity.id.in_(first_ids)).all()
    assert all(o.status == OpportunityStatus.STALE for o in stale)
