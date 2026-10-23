"""Create the durable OHLCV market data table.

Revision ID: 20261023_0001
Revises:
Create Date: 2026-10-23 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261023_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_data",
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("symbol", "timestamp", name="pk_market_data"),
    )


def downgrade() -> None:
    op.drop_table("market_data")
