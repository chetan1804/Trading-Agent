"""Store net realized P&L for paper exit fills.

Revision ID: 20261112_0014
Revises: 20261111_0013
Create Date: 2026-11-12 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261112_0014"
down_revision = "20261111_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("paper_executions", sa.Column("realized_pnl", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("paper_executions", "realized_pnl")
