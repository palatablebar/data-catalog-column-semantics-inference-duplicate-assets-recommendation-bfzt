"""通用序列化与公共 schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def user_payload(user) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
    }


def tag_payload(tag) -> dict[str, Any]:
    return {
        "id": str(tag.id),
        "tag_name": tag.tag_name,
        "category": tag.category,
        "source": tag.source,
        "confidence": round(tag.confidence, 3),
        "tagged_by": tag.tagged_by,
        "created_at": iso(tag.created_at),
    }


def column_brief(column) -> dict[str, Any]:
    return {
        "id": str(column.id),
        "column_name": column.column_name,
        "data_type": column.data_type,
        "inferred_type": column.inferred_type,
        "confidence": round(column.confidence or 0.0, 3),
        "inference_source": column.inference_source,
    }


def asset_brief(asset) -> dict[str, Any]:
    return {
        "id": str(asset.id),
        "asset_key": asset.asset_key,
        "table_name": asset.table_name,
        "schema_name": asset.schema_name,
        "layer": asset.layer,
        "domain": asset.domain,
        "row_count": asset.row_count,
        "column_count": asset.column_count,
    }


class MessageResponse(BaseModel):
    message: str
