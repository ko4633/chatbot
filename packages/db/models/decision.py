from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base
from packages.db.enums import DecisionType, WatchlistEntityType
from packages.db.mixins import TimestampMixin, UUIDPk


class UserDecision(Base, UUIDPk, TimestampMixin):
    __tablename__ = "user_decision"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opportunity.id"), index=True
    )
    user_email: Mapped[str] = mapped_column(String(255))
    decision: Mapped[DecisionType]
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    note: Mapped[str | None] = mapped_column(Text, default=None)


class WatchlistItem(Base, UUIDPk, TimestampMixin):
    __tablename__ = "watchlist_item"

    user_email: Mapped[str] = mapped_column(String(255))
    entity_type: Mapped[WatchlistEntityType]
    entity_ref: Mapped[str] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text, default=None)
