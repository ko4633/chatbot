from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.common import SourceRef
from packages.db.models.source import Source

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/{source_id}", response_model=SourceRef)
def get_source(source_id: uuid.UUID, db: Session = Depends(get_db)) -> SourceRef:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="source not found")
    return SourceRef.model_validate(source)
