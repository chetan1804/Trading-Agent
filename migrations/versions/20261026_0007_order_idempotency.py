"""Add unique idempotency keys to paper orders.

Revision ID: 20261026_0007
Revises: 20261026_0006
Create Date: 2026-10-26 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261026_0007"
down_revision = "20261026_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("paper_orders", sa.Column("idempotency_key", sa.String(length=128)))
    op.create_unique_constraint(
        "uq_paper_orders_idempotency_key", "paper_orders", ["idempotency_key"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_paper_orders_idempotency_key", "paper_orders", type_="unique")
    op.drop_column("paper_orders", "idempotency_key")
