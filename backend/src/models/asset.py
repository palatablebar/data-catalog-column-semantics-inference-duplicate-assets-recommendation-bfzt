"""数据资产（库/表/负责人/域/行数/更新时间）。"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Asset(Base):
    __tablename__ = "asset"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    schema_name: Mapped[str] = mapped_column(String(80), nullable=False)
    table_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    layer: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    owner_name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    columns: Mapped[list["AssetColumn"]] = relationship(  # noqa: F821
        back_populates="asset", cascade="all, delete-orphan", order_by="AssetColumn.ordinal"
    )
