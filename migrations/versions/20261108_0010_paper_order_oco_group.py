"""Persist OCO groups for paper exit orders.

Revision ID: 20261108_0010
Revises: 20261031_0009
Create Date: 2026-11-08 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261108_0010"
down_revision = "20261031_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("paper_orders", sa.Column("oco_group", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("paper_orders", "oco_group")
