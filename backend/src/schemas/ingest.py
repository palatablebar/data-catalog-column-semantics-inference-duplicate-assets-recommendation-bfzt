"""采集任务 schema。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class CreateJobRequest(BaseModel):
    job_name: str = Field(default="样例表列统计采集", min_length=2, max_length=120)
    connection_name: str = Field(default="pg-catmap-sample", max_length=120)
    scope: str = Field(default="5 张样例数据表", max_length=255)
