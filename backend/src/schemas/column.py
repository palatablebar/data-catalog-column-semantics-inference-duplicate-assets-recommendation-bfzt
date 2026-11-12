"""列类型推断 / 人工纠错 schema。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class InferRequest(BaseModel):
    force: bool = False


class CorrectTypeRequest(BaseModel):
    inferred_type: str = Field(min_length=2, max_length=20)
    note: str = Field(default="", max_length=200)
