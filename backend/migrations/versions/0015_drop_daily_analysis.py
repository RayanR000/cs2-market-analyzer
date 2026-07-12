"""Drop daily_analysis table (trend model removed).

The trend model has been replaced by the ML forecast system. The
daily_analysis table is no longer populated or queried.

Revision ID: 0015_drop_daily_analysis
Revises: 0014_add_forecast_outcomes
Create Date: 2026-07-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0015_drop_daily_analysis"
down_revision = "0014_add_forecast_outcomes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("daily_analysis")


def downgrade() -> None:
    op.create_table(
        "daily_analysis",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("analysis_date", sa.Date(), nullable=False),
        sa.Column("current_price", sa.Float(), nullable=True),
        sa.Column("ma_7day", sa.Float(), nullable=True),
        sa.Column("ma_30day", sa.Float(), nullable=True),
        sa.Column("ma_90day", sa.Float(), nullable=True),
        sa.Column("momentum_7day", sa.Float(), nullable=True),
        sa.Column("momentum_30day", sa.Float(), nullable=True),
        sa.Column("volatility", sa.Float(), nullable=True),
        sa.Column("trend_direction", sa.String(20), nullable=True),
        sa.Column("momentum_score", sa.Float(), nullable=True),
        sa.Column("opportunity_score", sa.Float(), nullable=True),
        sa.Column("trading_volume_trend", sa.Float(), nullable=True),
        sa.Column("price_stability", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_daily_analysis_item_date",
        "daily_analysis",
        ["item_id", "analysis_date"],
    )
    op.create_index(
        "idx_daily_analysis_item_date",
        "daily_analysis",
        ["item_id", "analysis_date"],
    )
