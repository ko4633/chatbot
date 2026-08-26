from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from packages.core.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception as e:  # noqa: BLE001 - health check must never itself 500 uninformatively
        database_status = f"error: {e}"
    return {
        "status": "ok",
        "database": database_status,
        "ai_enabled": settings.ai_effectively_enabled,
        "environment": settings.environment,
    }
