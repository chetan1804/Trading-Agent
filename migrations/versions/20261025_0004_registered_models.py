"""Persist trained model artifacts and registry metadata.

Revision ID: 20261025_0004
Revises: 20261024_0003
Create Date: 2026-10-25 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261025_0004"
down_revision = "20261024_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "registered_models",
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("model_type", sa.String(length=64), nullable=False),
        sa.Column("dataset_version", sa.String(length=80), nullable=False),
        sa.Column("training_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feature_names", sa.JSON(), nullable=False),
        sa.Column("hyperparameters", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("validation_metrics", sa.JSON(), nullable=False),
        sa.Column("split_rows", sa.JSON(), nullable=False),
        sa.Column("artifact", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("model_version", name="pk_registered_models"),
    )


def downgrade() -> None:
    op.drop_table("registered_models")
