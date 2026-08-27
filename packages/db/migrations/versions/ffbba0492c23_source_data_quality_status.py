"""source data quality status

Revision ID: ffbba0492c23
Revises: 6bc07a2e224c
Create Date: 2026-08-27 03:04:20.566448

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ffbba0492c23'
down_revision: Union[str, None] = '6bc07a2e224c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # data_quality_status: no existing source has ever been assessed, so
    # every row backfills unambiguously to HEALTHY (unlike data_mode, which
    # had to be derived per-row from is_mock) — add nullable, backfill, then
    # tighten to NOT NULL.
    quality_enum = sa.Enum(
        'HEALTHY', 'DEGRADED', 'STALE', 'QUARANTINED', 'FAILED', name='dataqualitystatus'
    )
    quality_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('source', sa.Column('data_quality_status', quality_enum, nullable=True))
    op.execute("UPDATE source SET data_quality_status = 'HEALTHY'::dataqualitystatus")
    op.alter_column('source', 'data_quality_status', nullable=False)
    op.add_column('source', sa.Column('last_quality_check_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('source', 'last_quality_check_at')
    op.drop_column('source', 'data_quality_status')
    sa.Enum(name='dataqualitystatus').drop(op.get_bind(), checkfirst=True)
