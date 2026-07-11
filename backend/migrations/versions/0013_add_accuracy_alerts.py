"""Add accuracy_alerts table for concept drift monitoring.

Revision ID: 0013_add_accuracy_alerts
Revises: 0012_drop_chart_points
Create Date: 2026-07-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0013_add_accuracy_alerts"
down_revision = "0012_drop_chart_points"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accuracy_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prediction_type", sa.String(50), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=True),
        sa.Column("sliding_window_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("current_accuracy", sa.Float(), nullable=False),
        sa.Column("threshold_accuracy", sa.Float(), nullable=False, server_default="60.0"),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("triggered_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_alert_type_triggered",
        "accuracy_alerts",
        ["prediction_type", "triggered_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_alert_type_triggered", table_name="accuracy_alerts")
    op.drop_table("accuracy_alerts")
