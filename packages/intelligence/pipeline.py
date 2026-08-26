"""Top-level pipeline orchestration: one AnalysisRun ties ingestion, entity
resolution, event detection, and opportunity/insight building together with
a single traceable id. See docs/MASTER_SPEC.md §4 and docs/ARCHITECTURE.md §2.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from packages.ai.base import AIProvider
from packages.collectors.base import Collector
from packages.collectors.runner import run_collector
from packages.collectors.storage import RawObjectStore
from packages.core.time_utils import utcnow
from packages.db.enums import AnalysisRunStatus, AnalysisRunType
from packages.db.models.opportunity import Opportunity
from packages.db.models.run import AnalysisRun
from packages.entities.pipeline import run_entity_resolution
from packages.intelligence import events
from packages.intelligence.insight_builder import build_insights_for_opportunity
from packages.intelligence.opportunity_builder import build_opportunities
from packages.observability.logging import bind_context, clear_context, get_logger

logger = get_logger(__name__)

PIPELINE_ALGORITHM_VERSION = "pipeline.v1"


def run_full_analysis(
    db: Session,
    ai_provider: AIProvider,
    collectors: list[Collector],
    raw_store: RawObjectStore,
    triggered_by: str,
) -> AnalysisRun:
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

        run.status = AnalysisRunStatus.PARTIAL if any_failures else AnalysisRunStatus.SUCCEEDED
        run.completed_at = utcnow()
        run.stats = {
            "collectors": collector_stats,
            "entity_resolution": vars(entity_stats),
            "events": vars(event_stats),
            "opportunities": vars(opp_stats),
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
