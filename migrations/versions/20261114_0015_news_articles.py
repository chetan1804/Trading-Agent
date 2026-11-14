"""Persist normalized news headlines and sentiment.

Revision ID: 20261114_0015
Revises: 20261112_0014
Create Date: 2026-11-14 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20261114_0015"
down_revision = "20261112_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "news_articles",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("headline", sa.String(length=1000), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sentiment", sa.String(length=16), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("content_hash", name="uq_news_articles_content_hash"),
    )
    op.create_index("ix_news_articles_symbol", "news_articles", ["symbol"])
    op.create_index("ix_news_articles_published_at", "news_articles", ["published_at"])


def downgrade() -> None:
    op.drop_index("ix_news_articles_published_at", table_name="news_articles")
    op.drop_index("ix_news_articles_symbol", table_name="news_articles")
    op.drop_table("news_articles")
