"""Add rarity, rarity_rank, weapon_type columns to items table.

Revision ID: 0017_add_item_rarity_columns
Revises: 0016_add_supply_snapshots
Create Date: 2026-07-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_add_item_rarity_columns"
down_revision = "0016_add_supply_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("items")}

    if "rarity" not in columns:
        op.add_column("items", sa.Column("rarity", sa.String(50), nullable=True))
    if "rarity_rank" not in columns:
        op.add_column("items", sa.Column("rarity_rank", sa.Integer(), nullable=True))
    if "weapon_type" not in columns:
        op.add_column("items", sa.Column("weapon_type", sa.String(50), nullable=True))

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE INDEX IF NOT EXISTS idx_item_rarity ON items (rarity)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_item_weapon_type ON items (weapon_type)")
    else:
        op.create_index("idx_item_rarity", "items", ["rarity"])
        op.create_index("idx_item_weapon_type", "items", ["weapon_type"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_item_rarity")
        op.execute("DROP INDEX IF EXISTS idx_item_weapon_type")
    else:
        op.drop_index("idx_item_rarity", table_name="items")
        op.drop_index("idx_item_weapon_type", table_name="items")
    op.drop_column("items", "rarity")
    op.drop_column("items", "rarity_rank")
    op.drop_column("items", "weapon_type")
