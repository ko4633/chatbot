"""Cross-cutting system status queries shared by apps/api routers — the
Live/Mock rollup is needed by both the /opportunities data-mode header and
the /health/dashboard endpoint, so it lives here once instead of being
duplicated or imported privately across router modules.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from packages.db.enums import DataMode, DataQualityStatus
from packages.db.models.source import Source


def system_data_mode(db: Session) -> str:
    """See docs/ARCHITECTURE.md §6 (Mock vs live confusion) and
    docs/ADR/0007-explicit-data-mode-field.md. Based on Source.data_mode
    (MOCK/LIVE/MANUAL), not the legacy is_mock boolean — a MANUAL source
    (a person typed in a real observed value) counts as non-mock here,
    same as LIVE, since it isn't fixture data either."""
    has_mock = db.query(Source).filter_by(data_mode=DataMode.MOCK).first() is not None
    has_non_mock = db.query(Source).filter(Source.data_mode != DataMode.MOCK).first() is not None
    if has_mock and has_non_mock:
        return "mixed"
    if has_non_mock:
        return "live"
    return "mock"


def collector_health_summary(db: Session) -> list[dict]:
    """One row per registered Source describing its data quality/liveness —
    the collector section of the health dashboard (product brief §18)."""
    sources = db.query(Source).all()
    return [
        {
            "name": s.name,
            "data_mode": s.data_mode.value,
            "data_quality_status": s.data_quality_status.value,
            "last_quality_check_at": (
                s.last_quality_check_at.isoformat() if s.last_quality_check_at else None
            ),
            "is_active": s.is_active,
            "usable_for_opportunities": s.data_quality_status
            not in (DataQualityStatus.FAILED, DataQualityStatus.QUARANTINED),
        }
        for s in sources
    ]
