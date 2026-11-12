"""相似表对：score 落库 + 合并建议 JSON + 人工状态。"""
from __future__ import annotations

import uuid

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class SimilarityPair(Base):
    __tablename__ = "similarity_pair"
    __table_args__ = (
        UniqueConstraint("left_asset_id", "right_asset_id", name="uq_similarity_pair"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    left_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset.id", ondelete="CASCADE"), nullable=False, index=True
    )
    right_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    jaccard: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    structure_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    method: Mapped[str] = mapped_column(String(40), nullable=False, default="minhash-lsh")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="recommended", index=True)
    suggestion: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    computed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
