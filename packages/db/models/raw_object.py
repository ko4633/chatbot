from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base
from packages.db.mixins import TimestampMixin, UUIDPk


class RawObject(Base, UUIDPk, TimestampMixin):
    """Content-addressed pointer into the raw data lake. See docs/DATA_MODEL.md
    and docs/MASTER_SPEC.md §4 (Raw Data Lake)."""

    __tablename__ = "raw_object"

    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    mime_type: Mapped[str] = mapped_column(String(255))
    byte_size: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(Text)
