"""Add an auditable record for each paper fill.

Revision ID: 20261109_0012
Revises: 20261109_0011
Create Date: 2026-11-09 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261109_0012"
down_revision = "20261109_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_executions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("order_id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=4), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("fees", sa.Float(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_price", sa.Float(), nullable=False),
        sa.Column("requested_quantity", sa.Float(), nullable=True),
        sa.Column("requested_fees", sa.Float(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["paper_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_paper_executions"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_paper_executions_idempotency_key"
        ),
    )
    op.create_index("ix_paper_executions_order_id", "paper_executions", ["order_id"])
    op.create_index("ix_paper_executions_symbol", "paper_executions", ["symbol"])
    op.create_index("ix_paper_executions_executed_at", "paper_executions", ["executed_at"])


def downgrade() -> None:
    op.drop_index("ix_paper_executions_executed_at", table_name="paper_executions")
    op.drop_index("ix_paper_executions_symbol", table_name="paper_executions")
    op.drop_index("ix_paper_executions_order_id", table_name="paper_executions")
    op.drop_table("paper_executions")
