"""Add icon_url, classid, instanceid columns to items table.

Revision ID: 0004_add_item_metadata_images
Revises: 0003_add_price_history_unique
Create Date: 2026-07-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_add_item_metadata_images"
down_revision = "0003_add_price_history_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("items")]

    if "icon_url" not in columns:
        op.add_column("items", sa.Column("icon_url", sa.String(length=512), nullable=True))
    if "classid" not in columns:
        op.add_column("items", sa.Column("classid", sa.String(length=64), nullable=True))
    if "instanceid" not in columns:
        op.add_column("items", sa.Column("instanceid", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("items", "icon_url")
    op.drop_column("items", "classid")
    op.drop_column("items", "instanceid")
