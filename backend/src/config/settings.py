"""集中配置：全部来自环境变量，默认值与 .env.example 保持一致。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # 数据库
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "catmap"
    db_user: str = "catmap"
    db_password: str = "catmap_pwd_2026"

    # 安全
    jwt_secret: str = "catmap-jwt-secret-change-me-2026-11"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120

    # 运行时
    redis_url: str = "redis://localhost:6379/0"
    sample_schema: str = "sample"
    export_dir: str = "/data/exports"
    seed_demo: bool = True
    inference_sample_limit: int = 200
    similarity_top_n: int = 6
    similarity_min_score: float = 0.45

    # 限流 / 配额
    rate_limit_per_minute: int = 240
    quota_admin: int = 5000
    quota_analyst: int = 2500
    quota_viewer: int = 1200

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
