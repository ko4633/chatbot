"""OMNIS worker CLI. Runs collectors + the analysis pipeline as one-shot
commands (docs/RUNBOOK.md). Phase 1 has no recurring scheduler — see
docs/ROADMAP.md Phase 2 (scheduling/alerts).
"""

from __future__ import annotations

import json

import typer

from packages.ai.factory import get_ai_provider
from packages.collectors.japan_marketplace import JapanMarketplaceProvider
from packages.collectors.korea_marketplace import KoreaMarketplaceProvider
from packages.collectors.storage import get_raw_object_store
from packages.core.settings import get_settings
from packages.db.base import get_session_factory
from packages.intelligence.pipeline import run_full_analysis
from packages.observability.logging import configure_logging
from packages.telegram.bot_runner import run_polling_loop

app = typer.Typer(help="OMNIS worker: ingestion + analysis pipeline")


def _all_collectors():
    return [JapanMarketplaceProvider(), KoreaMarketplaceProvider()]


@app.command()
def seed() -> None:
    """Load the bundled JP/KR demo fixtures and run the full analysis
    pipeline once. Safe to re-run (idempotent ingestion)."""
    settings = get_settings()
    configure_logging(settings.log_level)
    session_factory = get_session_factory()
    db = session_factory()
    try:
        run = run_full_analysis(
            db,
            get_ai_provider(settings),
            _all_collectors(),
            get_raw_object_store(settings),
            triggered_by="worker:seed",
        )
        typer.echo(f"AnalysisRun {run.id} finished with status={run.status.value}")
        typer.echo(json.dumps(run.stats, indent=2, default=str))
    finally:
        db.close()


@app.command(name="run-pipeline")
def run_pipeline() -> None:
    """Re-run collectors + the full analysis pipeline (same as `seed`, named
    for the recurring-run case once new fixture data is added)."""
    seed()


@app.command()
def status() -> None:
    """Print the most recent AnalysisRun."""
    from packages.db.models.run import AnalysisRun

    session_factory = get_session_factory()
    db = session_factory()
    try:
        run = db.query(AnalysisRun).order_by(AnalysisRun.started_at.desc()).first()
        if run is None:
            typer.echo("No AnalysisRun recorded yet. Run `seed` first.")
            raise typer.Exit(code=1)
        typer.echo(
            f"{run.id} | {run.run_type.value} | {run.status.value} | started {run.started_at}"
        )
        typer.echo(json.dumps(run.stats, indent=2, default=str))
    finally:
        db.close()


@app.command(name="telegram-bot")
def telegram_bot() -> None:
    """Run the personal-bot long-polling loop (docs/ADR/0010). Requires
    TELEGRAM_BOT_TOKEN to be configured; exits immediately with a warning
    otherwise rather than silently doing nothing forever."""
    settings = get_settings()
    configure_logging(settings.log_level)
    if not settings.telegram_effectively_enabled:
        typer.echo("Telegram is not configured (TELEGRAM_BOT_TOKEN missing) — nothing to run.")
        raise typer.Exit(code=1)
    typer.echo("Starting Telegram bot long-polling loop. Ctrl+C to stop.")
    run_polling_loop(settings)


if __name__ == "__main__":
    app()
