"""FX ingestion, history, staleness, and change-detection — the parts of the
Phase 2 FX engine that touch the database. Requires a real Postgres (see
tests/conftest.py), same as the other tests/integration modules.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from packages.core.time_utils import utcnow
from packages.db.enums import AnalysisRunStatus, AnalysisRunType, DataMode, EventType
from packages.db.models.fx import FXObservation
from packages.db.models.run import AnalysisRun
from packages.db.models.source import Source
from packages.fx.ingest import DEFAULT_PAIRS, ingest_fx_rates
from packages.fx.manual_provider import ManualFXProvider
from packages.intelligence import events, facts


def _make_analysis_run(db) -> uuid.UUID:
    run = AnalysisRun(
        run_type=AnalysisRunType.FULL,
        status=AnalysisRunStatus.RUNNING,
        started_at=utcnow(),
        triggered_by="pytest",
        algorithm_version="test",
    )
    db.add(run)
    db.flush()
    return run.id


def test_ingest_fx_rates_writes_observations_with_mock_data_mode(clean_db):
    stats = ingest_fx_rates(clean_db, ManualFXProvider())
    clean_db.commit()

    assert stats.pairs_attempted == len(DEFAULT_PAIRS)
    assert stats.pairs_succeeded == len(DEFAULT_PAIRS)
    assert stats.pairs_failed == 0

    obs = facts.latest_fx(clean_db, "JPY", "KRW")
    assert obs is not None
    assert float(obs.rate) > 0

    source = clean_db.get(Source, obs.source_id)
    assert source.data_mode == DataMode.MOCK
    assert source.is_mock is True


def test_ingest_fx_rates_is_idempotent(clean_db):
    ingest_fx_rates(clean_db, ManualFXProvider())
    clean_db.commit()
    first_count = clean_db.query(FXObservation).count()

    ingest_fx_rates(clean_db, ManualFXProvider())
    clean_db.commit()
    second_count = clean_db.query(FXObservation).count()

    assert second_count == first_count


def test_fx_history_and_as_of_queries(clean_db):
    ingest_fx_rates(clean_db, ManualFXProvider())
    clean_db.commit()

    history = facts.fx_history(clean_db, "JPY", "KRW")
    assert len(history) == 1  # ManualFXProvider.get_latest only ever writes one point
    assert history[-1].observed_at <= utcnow()


def test_is_fx_stale_true_when_no_observation():
    assert facts.is_fx_stale(None, stale_after_hours=48) is True


def test_is_fx_stale_false_for_recent_observation(clean_db):
    ingest_fx_rates(clean_db, ManualFXProvider())
    clean_db.commit()
    obs = facts.latest_fx(clean_db, "JPY", "KRW")
    # config/fx_rates.yaml's "latest" observed_at is within the last few
    # days of this test suite's development window — well under 48h * 30.
    assert facts.is_fx_stale(obs, stale_after_hours=24 * 365) is False


def test_is_fx_stale_true_for_old_observation(clean_db):
    ingest_fx_rates(clean_db, ManualFXProvider())
    clean_db.commit()
    obs = clean_db.query(FXObservation).filter_by(base_currency="JPY", quote_currency="KRW").one()
    obs.observed_at = utcnow() - timedelta(hours=1000)
    clean_db.commit()
    assert facts.is_fx_stale(obs, stale_after_hours=48) is True


def test_detect_fx_events_fires_on_significant_move(clean_db):
    source = Source(
        name="Test FX Source",
        source_type="FIXTURE",
        trust_tier="UNKNOWN",
        factual_reliability="MEDIUM",
        signal_value="HIGH",
        is_mock=True,
        data_mode=DataMode.MOCK,
    )
    clean_db.add(source)
    clean_db.flush()

    base_time = utcnow() - timedelta(days=1)
    clean_db.add(
        FXObservation(
            base_currency="JPY",
            quote_currency="KRW",
            rate=9.30,
            provider_name="manual",
            is_live=False,
            source_id=source.id,
            retrieved_at=base_time,
            observed_at=base_time,
            extraction_method="FIXTURE",
            confidence=0.7,
        )
    )
    clean_db.add(
        FXObservation(
            base_currency="JPY",
            quote_currency="KRW",
            rate=9.80,  # +5.4% move, well above FX_CHANGE_THRESHOLD_PCT (1%)
            provider_name="manual",
            is_live=False,
            source_id=source.id,
            retrieved_at=utcnow(),
            observed_at=utcnow(),
            extraction_method="FIXTURE",
            confidence=0.7,
        )
    )
    clean_db.commit()

    stats = events.detect_fx_events(clean_db, _make_analysis_run(clean_db))
    clean_db.commit()

    assert stats.events_created == 1
    from packages.db.models.event import Event

    event = clean_db.query(Event).filter_by(event_type=EventType.FX_MOVE).one()
    assert event.change_pct > 0
    assert event.entity_id == events.fx_pair_entity_id("JPY", "KRW")


def test_detect_fx_events_is_idempotent(clean_db):
    source = Source(
        name="Test FX Source",
        source_type="FIXTURE",
        trust_tier="UNKNOWN",
        factual_reliability="MEDIUM",
        signal_value="HIGH",
        is_mock=True,
        data_mode=DataMode.MOCK,
    )
    clean_db.add(source)
    clean_db.flush()
    base_time = utcnow() - timedelta(days=1)
    for rate, when in ((9.30, base_time), (9.80, utcnow())):
        clean_db.add(
            FXObservation(
                base_currency="JPY",
                quote_currency="KRW",
                rate=rate,
                provider_name="manual",
                is_live=False,
                source_id=source.id,
                retrieved_at=when,
                observed_at=when,
                extraction_method="FIXTURE",
                confidence=0.7,
            )
        )
    clean_db.commit()

    run_id = _make_analysis_run(clean_db)
    clean_db.commit()
    first = events.detect_fx_events(clean_db, run_id)
    clean_db.commit()
    second = events.detect_fx_events(clean_db, run_id)
    clean_db.commit()

    assert first.events_created == 1
    assert second.events_created == 0
