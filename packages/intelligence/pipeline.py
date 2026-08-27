"""Top-level pipeline orchestration: one AnalysisRun ties ingestion, FX,
entity resolution, event detection, and opportunity/insight building
together with a single traceable id. See docs/MASTER_SPEC.md §4 and
docs/ARCHITECTURE.md §2.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from packages.ai.base import AIProvider
from packages.collectors.base import Collector
from packages.collectors.quality import assess_collector_run, effective_yield_from_stats
from packages.collectors.runner import run_collector
from packages.collectors.storage import RawObjectStore
from packages.core.settings import get_settings
from packages.core.time_utils import utcnow
from packages.db.enums import AnalysisRunStatus, AnalysisRunType
from packages.db.models.opportunity import Opportunity
from packages.db.models.run import AnalysisRun
from packages.db.models.source import Source
from packages.entities.pipeline import run_entity_resolution
from packages.fx.factory import get_fx_provider
from packages.fx.ingest import ingest_fx_rates
from packages.fx.provider import FXProvider
from packages.intelligence import events
from packages.intelligence.insight_builder import build_insights_for_opportunity
from packages.intelligence.opportunity_builder import build_opportunities
from packages.observability.logging import bind_context, clear_context, get_logger
from packages.telegram.broadcast import broadcast_new_opportunities
from packages.telegram.factory import get_telegram_adapter

logger = get_logger(__name__)

PIPELINE_ALGORITHM_VERSION = "pipeline.v2"


def run_full_analysis(
    db: Session,
    ai_provider: AIProvider,
    collectors: list[Collector],
    raw_store: RawObjectStore,
    triggered_by: str,
    fx_provider: FXProvider | None = None,
) -> AnalysisRun:
    fx_provider = fx_provider or get_fx_provider(get_settings())
    run = AnalysisRun(
        run_type=AnalysisRunType.FULL,
        status=AnalysisRunStatus.RUNNING,
        started_at=utcnow(),
        triggered_by=triggered_by,
        algorithm_version=PIPELINE_ALGORITHM_VERSION,
        stats={},
    )
    db.add(run)
    db.flush()
    bind_context(analysis_run_id=str(run.id))
    logger.info("analysis_run_started", triggered_by=triggered_by)

    try:
        previous_run = (
            db.query(AnalysisRun)
            .filter(AnalysisRun.id != run.id)
            .order_by(AnalysisRun.created_at.desc())
            .first()
        )
        previous_collector_stats = (previous_run.stats or {}).get("collectors", {}) if previous_run else {}

        collector_stats = {}
        any_failures = False
        for collector in collectors:
            result = run_collector(db, collector, raw_store)
            collector_stats[collector.source_name] = {
                "items_seen": result.items_seen,
                "items_succeeded": result.items_succeeded,
                "items_failed": result.items_failed,
                "items_skipped_duplicate": result.items_skipped_duplicate,
                "observations_written": result.observations_written,
            }
            if result.items_failed:
                any_failures = True

            # Data quality: 200-OK-but-degraded detection (product brief
            # §16) — compares this run's yield against the same collector's
            # previous run, never an LLM judgment call.
            previous_stats_for_collector = previous_collector_stats.get(collector.source_name)
            previous_effective_yield = (
                effective_yield_from_stats(previous_stats_for_collector)
                if previous_stats_for_collector is not None
                else None
            )
            quality_status = assess_collector_run(result, previous_effective_yield)
            source = db.query(Source).filter_by(name=collector.source_name).one()
            source.data_quality_status = quality_status
            source.last_quality_check_at = utcnow()
        db.commit()

        fx_stats = ingest_fx_rates(db, fx_provider)
        if fx_stats.pairs_failed:
            any_failures = True
        db.commit()

        fx_event_stats = events.detect_fx_events(db, run.id)
        db.commit()

        entity_stats = run_entity_resolution(db, ai_provider, analysis_run_id=run.id)
        db.commit()

        event_stats = events.detect_price_events(db, run.id)
        db.commit()

        opp_stats = build_opportunities(db, run.id)
        db.commit()

        new_opportunities = db.query(Opportunity).filter_by(analysis_run_id=run.id).all()
        for opp in new_opportunities:
            build_insights_for_opportunity(db, ai_provider, opp, run.id)
        db.commit()

        settings = get_settings()
        broadcast_stats = None
        if settings.telegram_effectively_enabled and settings.telegram_broadcast_enabled:
            broadcast_stats = vars(
                broadcast_new_opportunities(
                    db,
                    get_telegram_adapter(settings),
                    run.id,
                    settings.telegram_chat_id,
                    min_score=settings.telegram_broadcast_min_score,
                )
            )

        run.status = AnalysisRunStatus.PARTIAL if any_failures else AnalysisRunStatus.SUCCEEDED
        run.completed_at = utcnow()
        run.stats = {
            "collectors": collector_stats,
            "fx": vars(fx_stats),
            "fx_events": vars(fx_event_stats),
            "entity_resolution": vars(entity_stats),
            "events": vars(event_stats),
            "opportunities": vars(opp_stats),
            "telegram": broadcast_stats,
        }
        db.add(run)
        db.commit()
        logger.info("analysis_run_completed", status=run.status.value, stats=run.stats)
        return run
    except Exception as e:
        db.rollback()
        run.status = AnalysisRunStatus.FAILED
        run.completed_at = utcnow()
        run.error_detail = str(e)
        db.add(run)
        db.commit()
        logger.error("analysis_run_failed", error=str(e))
        raise
    finally:
        clear_context()
