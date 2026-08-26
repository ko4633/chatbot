"""Research: new external collection + multi-step analysis, kept a distinct
endpoint from /search (docs/MASTER_SPEC.md §29/§30). Not implemented in
Phase 1 — see docs/ROADMAP.md Phase 5 (Autonomous Research). Returning a
templated stub here would misrepresent capability that doesn't exist yet;
501 is the honest response.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/research", tags=["research"])


@router.post("")
def start_research() -> None:
    raise HTTPException(
        status_code=501,
        detail="Autonomous research is not implemented in Phase 1. See docs/ROADMAP.md Phase 5.",
    )
