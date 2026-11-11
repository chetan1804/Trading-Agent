"""Persist paper-account equity observations for historical performance.

Revision ID: 20261111_0013
Revises: 20261109_0012
Create Date: 2026-11-11 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261111_0013"
down_revision = "20261109_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_equity_snapshots",
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("equity", sa.Float(), nullable=False),
        sa.Column("exposure", sa.Float(), nullable=False),
        sa.Column("realized_pnl", sa.Float(), nullable=False),
        sa.Column("unrealized_pnl", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("event_id", name="pk_paper_equity_snapshots"),
    )
    op.create_index(
        "ix_paper_equity_snapshots_captured_at",
        "paper_equity_snapshots",
        ["captured_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_paper_equity_snapshots_captured_at", table_name="paper_equity_snapshots")
    op.drop_table("paper_equity_snapshots")
