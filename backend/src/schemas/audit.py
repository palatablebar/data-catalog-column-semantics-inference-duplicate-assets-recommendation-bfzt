"""审计日志 schema。"""
from __future__ import annotations

from pydantic import BaseModel


class AuditQuery(BaseModel):
    limit: int = 50
