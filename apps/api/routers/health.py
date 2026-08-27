from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from packages.collectors.storage import get_raw_object_store
from packages.core.redis_client import get_redis_client
from packages.core.settings import get_settings
from packages.intelligence import facts
from packages.intelligence.opportunity_builder import FX_BASE_CURRENCY, FX_QUOTE_CURRENCY
from packages.intelligence.system_status import collector_health_summary, system_data_mode

router = APIRouter(tags=["health"])


def _check_database(db: Session) -> str:
    try:
        db.execute(text("SELECT 1"))
        return "ok"
    except Exception as e:  # noqa: BLE001 - health check must never itself 500 uninformatively
        return f"error: {e}"


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "database": _check_database(db),
        "ai_enabled": settings.ai_effectively_enabled,
        "environment": settings.environment,
    }


@router.get("/health/dashboard")
def health_dashboard(db: Session = Depends(get_db)) -> dict:
    """One-screen operability view (product brief §18): DB/Redis/raw-store
    connectivity, FX freshness, per-collector data quality, AI/Telegram
    configuration, and the system-wide Live-vs-Mock rollup. Every check is a
    live probe against the real dependency, not a cached or assumed value."""
    settings = get_settings()

    try:
        get_redis_client(settings).ping()
        redis_status = "ok"
    except Exception as e:  # noqa: BLE001 - same rationale as _check_database
        redis_status = f"error: {e}"

    try:
        get_raw_object_store(settings)  # constructing it exercises real connectivity (MinIO) or a local mkdir
        raw_store_status = "ok"
    except Exception as e:  # noqa: BLE001
        raw_store_status = f"error: {e}"

    fx_observation = facts.latest_fx(db, FX_BASE_CURRENCY, FX_QUOTE_CURRENCY)
    fx_status = {
        "pair": f"{FX_BASE_CURRENCY}/{FX_QUOTE_CURRENCY}",
        "provider": fx_observation.provider_name if fx_observation else None,
        "observed_at": fx_observation.observed_at.isoformat() if fx_observation else None,
        "is_stale": facts.is_fx_stale(fx_observation, settings.fx_stale_hours),
        "configured_provider": settings.fx_provider,
    }

    return {
        "status": "ok",
        "environment": settings.environment,
        "database": _check_database(db),
        "redis": redis_status,
        "raw_store": {"backend": settings.raw_store_backend, "status": raw_store_status},
        "fx": fx_status,
        "collectors": collector_health_summary(db),
        "ai": {
            "enabled": settings.ai_effectively_enabled,
            "configured": settings.ai_enabled,
        },
        "telegram": {
            "enabled": settings.telegram_effectively_enabled,
            "configured": bool(settings.telegram_bot_token),
        },
        "data_mode": system_data_mode(db),
    }
