"""Persist strategy signal and risk decisions.

Revision ID: 20261026_0006
Revises: 20261025_0005
Create Date: 2026-10-26 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261026_0006"
down_revision = "20261025_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategy_decisions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("signal_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", sa.String(length=8), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("risk_reason", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("order_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_strategy_decisions"),
    )
    op.create_index("ix_strategy_decisions_strategy_id", "strategy_decisions", ["strategy_id"])
    op.create_index("ix_strategy_decisions_symbol", "strategy_decisions", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_strategy_decisions_symbol", table_name="strategy_decisions")
    op.drop_index("ix_strategy_decisions_strategy_id", table_name="strategy_decisions")
    op.drop_table("strategy_decisions")
