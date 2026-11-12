"""worker 侧配置：沿用 backend 的环境变量约定。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "catmap"
    db_user: str = "catmap"
    db_password: str = "catmap_pwd_2026"
    redis_url: str = "redis://redis:6379/0"
    sample_schema: str = "sample"
    inference_sample_limit: int = 200

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()


settings = get_settings()
