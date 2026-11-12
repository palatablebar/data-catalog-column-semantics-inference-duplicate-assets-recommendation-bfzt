"""相似表 / 合并建议 schema。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class RecomputeRequest(BaseModel):
    top_n: int = Field(default=6, ge=1, le=50)
    min_score: float = Field(default=0.45, ge=0.0, le=1.0)


class DismissRequest(BaseModel):
    note: str = Field(default="人工确认非重复", max_length=200)
