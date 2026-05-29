"""Initial schema baseline.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-29
"""

from __future__ import annotations

from alembic import op

from database import Base

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
