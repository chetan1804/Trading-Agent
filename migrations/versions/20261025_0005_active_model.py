"""Track the model promoted for default inference.

Revision ID: 20261025_0005
Revises: 20261025_0004
Create Date: 2026-10-25 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261025_0005"
down_revision = "20261025_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "active_models",
        sa.Column("slot", sa.String(length=32), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("slot", name="pk_active_models"),
        sa.ForeignKeyConstraint(
            ["model_version"], ["registered_models.model_version"], name="fk_active_models_version"
        ),
    )


def downgrade() -> None:
    op.drop_table("active_models")
