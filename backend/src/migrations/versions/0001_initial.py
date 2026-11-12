"""初始化 catmap 平台表（asset / asset_column / semantic_tag / similarity_pair / ingest_job / audit_log / user）。

Revision ID: 0001_initial
"""
from __future__ import annotations

from alembic import op

from src.models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
