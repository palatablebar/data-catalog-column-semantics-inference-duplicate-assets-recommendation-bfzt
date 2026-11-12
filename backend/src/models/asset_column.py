"""资产列：名录/类型/样例值/统计 JSON/推断结果。"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class AssetColumn(Base):
    __tablename__ = "asset_column"
    __table_args__ = (UniqueConstraint("asset_id", "column_name", name="uq_asset_column_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    column_name: Mapped[str] = mapped_column(String(120), nullable=False)
    data_type: Mapped[str] = mapped_column(String(40), nullable=False, default="text")
    nullable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    comment: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    sample_values: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    inferred_type: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    inference_source: Mapped[str | None] = mapped_column(String(12), nullable=True)
    evidence: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    candidates: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    profiled_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    asset: Mapped["Asset"] = relationship(back_populates="columns")  # noqa: F821
