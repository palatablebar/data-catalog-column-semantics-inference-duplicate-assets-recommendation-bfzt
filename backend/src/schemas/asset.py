"""资产检索 schema。"""
from __future__ import annotations

from pydantic import BaseModel


class AssetListQuery(BaseModel):
    layer: str | None = None
    domain: str | None = None
    q: str | None = None
    source_kind: str | None = None
    page: int = 1
    page_size: int = 20
