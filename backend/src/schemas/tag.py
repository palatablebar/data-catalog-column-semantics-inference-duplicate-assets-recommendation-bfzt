"""语义标签 schema。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class CreateTagRequest(BaseModel):
    column_id: str
    tag_name: str = Field(min_length=2, max_length=60)
    category: str = Field(default="pii", max_length=20)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class BulkTagRequest(BaseModel):
    column_ids: list[str] = Field(min_length=1, max_length=200)
    tag_name: str = Field(min_length=2, max_length=60)
    category: str = Field(default="pii", max_length=20)
