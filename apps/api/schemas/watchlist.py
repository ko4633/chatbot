from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class WatchlistItemCreate(BaseModel):
    user_email: str
    entity_type: str
    entity_ref: str
    note: str | None = None


class WatchlistItemRead(BaseModel):
    id: uuid.UUID
    user_email: str
    entity_type: str
    entity_ref: str
    note: str | None
    created_at: datetime
