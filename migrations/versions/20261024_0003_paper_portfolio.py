"""Persist the paper portfolio snapshot.

Revision ID: 20261024_0003
Revises: 20261023_0002
Create Date: 2026-10-24 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261024_0003"
down_revision = "20261023_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_portfolios",
        sa.Column("account_id", sa.String(length=32), nullable=False),
        sa.Column("initial_cash", sa.Float(), nullable=False),
        sa.Column("cash", sa.Float(), nullable=False),
        sa.Column("positions", sa.JSON(), nullable=False),
        sa.Column("last_prices", sa.JSON(), nullable=False),
        sa.Column("position_cost_basis", sa.JSON(), nullable=False),
        sa.Column("realized_pnl", sa.Float(), nullable=False),
        sa.Column("daily_pnl", sa.Float(), nullable=False),
        sa.Column("peak_equity", sa.Float(), nullable=False),
        sa.Column("last_trade_at_by_symbol", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("account_id", name="pk_paper_portfolios"),
    )


def downgrade() -> None:
    op.drop_table("paper_portfolios")
