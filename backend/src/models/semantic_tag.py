"""语义标签：manual 人工 / inferred 算法推断，含置信度。"""
from __future__ import annotations

import uuid

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class SemanticTag(Base):
    __tablename__ = "semantic_tag"
    __table_args__ = (UniqueConstraint("asset_column_id", "tag_name", name="uq_tag_column_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_column_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_column.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag_name: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(12), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    tagged_by: Mapped[str] = mapped_column(String(160), nullable=False, default="system")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    column: Mapped["AssetColumn"] = relationship()  # noqa: F821
