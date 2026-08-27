from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.watchlist import WatchlistItemCreate, WatchlistItemRead
from packages.db.enums import WatchlistEntityType
from packages.db.models.decision import WatchlistItem

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistItemRead])
def list_watchlist(user_email: str, db: Session = Depends(get_db)) -> list[WatchlistItemRead]:
    items = db.query(WatchlistItem).filter_by(user_email=user_email).all()
    return [WatchlistItemRead.model_validate(i, from_attributes=True) for i in items]


@router.post("", response_model=WatchlistItemRead, status_code=201)
def add_watchlist_item(
    payload: WatchlistItemCreate, db: Session = Depends(get_db)
) -> WatchlistItemRead:
    try:
        entity_type = WatchlistEntityType(payload.entity_type)
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"invalid entity_type: {payload.entity_type}"
        ) from e
    item = WatchlistItem(
        user_email=payload.user_email,
        entity_type=entity_type,
        entity_ref=payload.entity_ref,
        note=payload.note,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return WatchlistItemRead.model_validate(item, from_attributes=True)


@router.delete("/{item_id}", status_code=204)
def remove_watchlist_item(item_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    item = db.get(WatchlistItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="watchlist item not found")
    db.delete(item)
    db.commit()
