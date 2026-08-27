"""OMNIS API — the only backend surface apps/web talks to. Never imports an
AI vendor SDK or exposes a secret to the frontend (docs/SECURITY.md §1)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import health, opportunities, research, search, sources, watchlist
from packages.core.settings import get_settings
from packages.observability.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="OMNIS API",
        description="Personal Intelligence OS — Phase 1 (Product Intelligence Foundation)",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.environment == "development" else [],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(opportunities.router)
    app.include_router(sources.router)
    app.include_router(watchlist.router)
    app.include_router(search.router)
    app.include_router(research.router)

    return app


app = create_app()
