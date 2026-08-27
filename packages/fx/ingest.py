"""Persists FXProvider output as FXObservation rows. Mirrors
packages/collectors/runner.py's idempotency pattern (unique natural key,
get-or-create Source) at a much smaller scale — FX has no "page" to
snapshot, so there is no RawObject/SourceSnapshot here, just the
observation itself with full provenance (docs/DATA_MODEL.md `fx_observation`).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from packages.db.enums import DataMode, ExtractionMethod, ReliabilityLevel, SourceType, TrustTier
from packages.db.models.fx import FXObservation
from packages.db.models.source import Source
from packages.fx.provider import FXProvider
from packages.fx.types import FXRateNotFound
from packages.observability.logging import get_logger

logger = get_logger(__name__)

DEFAULT_PAIRS = (("JPY", "KRW"), ("USD", "KRW"), ("EUR", "KRW"))


@dataclass
class FXIngestStats:
    pairs_attempted: int = 0
    pairs_succeeded: int = 0
    pairs_failed: int = 0
    errors: list[str] = field(default_factory=list)


def _get_or_create_fx_source(db: Session, provider: FXProvider, source_name: str, is_live: bool) -> Source:
    source = db.query(Source).filter_by(name=source_name).one_or_none()
    if source:
        return source
    source = Source(
        name=source_name,
        source_type=SourceType.MARKETPLACE_API if is_live else SourceType.FIXTURE,
        trust_tier=TrustTier.OFFICIAL if is_live else TrustTier.UNKNOWN,
        factual_reliability=ReliabilityLevel.HIGH if is_live else ReliabilityLevel.MEDIUM,
        signal_value=ReliabilityLevel.HIGH,
        country=None,
        base_url=None,
        is_mock=not is_live,
        data_mode=DataMode.LIVE if is_live else DataMode.MOCK,
    )
    db.add(source)
    db.flush()
    return source


def ingest_fx_rates(
    db: Session, provider: FXProvider, pairs: tuple[tuple[str, str], ...] = DEFAULT_PAIRS
) -> FXIngestStats:
    stats = FXIngestStats()
    for base, quote in pairs:
        stats.pairs_attempted += 1
        try:
            result = provider.get_latest(base, quote)
        except FXRateNotFound as e:
            stats.pairs_failed += 1
            stats.errors.append(f"{base}/{quote}: {e}")
            logger.warning("fx_ingest_failed", pair=f"{base}/{quote}", error=str(e))
            continue

        source = _get_or_create_fx_source(db, provider, result.source_name, result.is_live)

        exists = (
            db.query(FXObservation)
            .filter_by(
                base_currency=result.base_currency,
                quote_currency=result.quote_currency,
                source_id=source.id,
                observed_at=result.observed_at,
            )
            .first()
        )
        if exists:
            stats.pairs_succeeded += 1  # idempotent: already have this exact observation
            continue

        db.add(
            FXObservation(
                base_currency=result.base_currency,
                quote_currency=result.quote_currency,
                rate=result.rate,
                provider_name=result.provider_name,
                is_live=result.is_live,
                source_id=source.id,
                retrieved_at=result.retrieved_at,
                observed_at=result.observed_at,
                parser_name="",
                parser_version="",
                extraction_method=ExtractionMethod.API_RESPONSE
                if result.is_live
                else ExtractionMethod.FIXTURE,
                confidence=result.confidence,
            )
        )
        db.flush()
        stats.pairs_succeeded += 1
    return stats
