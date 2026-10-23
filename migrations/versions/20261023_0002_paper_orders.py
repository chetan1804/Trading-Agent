"""Persist paper order state.

Revision ID: 20261023_0002
Revises: 20261023_0001
Create Date: 2026-10-23 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261023_0002"
down_revision = "20261023_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_orders",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=4), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("order_type", sa.String(length=8), nullable=False),
        sa.Column("limit_price", sa.Float(), nullable=True),
        sa.Column("stop_price", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("filled_quantity", sa.Float(), nullable=False),
        sa.Column("avg_fill_price", sa.Float(), nullable=True),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_paper_orders"),
    )
    op.create_index("ix_paper_orders_symbol", "paper_orders", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_paper_orders_symbol", table_name="paper_orders")
    op.drop_table("paper_orders")
