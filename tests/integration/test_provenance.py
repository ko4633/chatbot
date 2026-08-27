"""Every external observation keeps its source, retrieved_at, and
observed_at (CLAUDE.md "do not remove provenance"; docs/DATA_MODEL.md §3).
These tests check the real rows written by a full pipeline run, not just
that the schema *could* carry provenance.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from packages.ai.null_provider import NullAIProvider
from packages.collectors.japan_marketplace import JapanMarketplaceProvider
from packages.collectors.korea_marketplace import KoreaMarketplaceProvider
from packages.collectors.storage import LocalFileStore
from packages.db.enums import ExtractionMethod
from packages.db.models.fx import FXObservation
from packages.db.models.observations import PriceObservation
from packages.db.models.opportunity import Opportunity
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


def test_every_price_observation_has_full_provenance(clean_db, tmp_path):
    _run_pipeline(clean_db, tmp_path)
    observations = clean_db.query(PriceObservation).all()
    assert len(observations) > 0
    for obs in observations:
        assert obs.source_id is not None
        assert obs.source_snapshot_id is not None
        assert obs.retrieved_at is not None
        assert obs.observed_at is not None
        assert obs.extraction_method is not None


def test_every_fx_observation_has_source_and_provider_recorded(clean_db, tmp_path):
    _run_pipeline(clean_db, tmp_path)
    fx_observations = clean_db.query(FXObservation).all()
    assert len(fx_observations) > 0
    for obs in fx_observations:
        assert obs.source_id is not None
        assert obs.provider_name
        assert obs.retrieved_at is not None
        assert obs.observed_at is not None
        assert obs.is_live is False  # ManualFXProvider — must be honestly labeled, not LIVE


def test_fx_observation_source_id_is_not_nullable_at_the_schema_level(clean_db):
    # Behavioral proof, not just a convention: the DB itself rejects an
    # FXObservation with no source, unlike Insight/Opportunity where
    # ProvenanceMixin.source_id is nullable by design (aggregate rows).
    clean_db.add(
        FXObservation(
            base_currency="JPY",
            quote_currency="KRW",
            rate=9.3,
            provider_name="manual",
            is_live=False,
            source_id=None,
            retrieved_at=None,
            observed_at=None,
            extraction_method=ExtractionMethod.FIXTURE,
            confidence=0.7,
        )
    )
    with pytest.raises(IntegrityError):
        clean_db.commit()
    clean_db.rollback()


def test_every_opportunity_has_retrieved_and_observed_at(clean_db, tmp_path):
    _run_pipeline(clean_db, tmp_path)
    opportunities = clean_db.query(Opportunity).all()
    assert len(opportunities) > 0
    for opp in opportunities:
        assert opp.retrieved_at is not None
        assert opp.observed_at is not None
        assert opp.extraction_method == ExtractionMethod.DERIVED
