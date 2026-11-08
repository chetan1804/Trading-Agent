"""Persist the last processed paper market bar timestamp per symbol.

Revision ID: 20261109_0011
Revises: 20261108_0010
Create Date: 2026-11-09 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261109_0011"
down_revision = "20261108_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "paper_portfolios",
        sa.Column(
            "last_market_timestamp_by_symbol",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("paper_portfolios", "last_market_timestamp_by_symbol")
