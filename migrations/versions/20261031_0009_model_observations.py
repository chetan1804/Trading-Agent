"""Store model input baselines, predictions, and eventual outcomes.

Revision ID: 20261031_0009
Revises: 20261027_0008
Create Date: 2026-10-31 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261031_0009"
down_revision = "20261027_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "registered_models",
        sa.Column("feature_baseline", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_table(
        "model_predictions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("prediction", sa.Integer(), nullable=False),
        sa.Column("actual_label", sa.Integer(), nullable=True),
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_model_predictions"),
    )
    op.create_index(
        "ix_model_predictions_model_version",
        "model_predictions",
        ["model_version"],
    )


def downgrade() -> None:
    op.drop_index("ix_model_predictions_model_version", table_name="model_predictions")
    op.drop_table("model_predictions")
    op.drop_column("registered_models", "feature_baseline")
