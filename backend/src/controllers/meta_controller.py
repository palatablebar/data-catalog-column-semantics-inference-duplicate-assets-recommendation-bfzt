"""健康检查与全局概览。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.config.database import ping_db
from src.config.settings import settings
from src.models.asset import Asset
from src.models.asset_column import AssetColumn
from src.models.ingest_job import IngestJob
from src.models.semantic_tag import SemanticTag
from src.models.similarity_pair import SimilarityPair
from src.utils.redis_client import get_redis


def _redis_ok() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception:  # noqa: BLE001
        return False


def health(db: Session) -> dict:
    return {
        "status": "ok",
        "service": "catmap-backend",
        "db": ping_db(),
        "redis": _redis_ok(),
        "seed_demo": settings.seed_demo,
        "checks": {"status": "ok"},
    }


def overview(db: Session) -> dict:
    def count(model) -> int:
        return db.scalar(select(func.count()).select_from(model)) or 0

    pending_pairs = db.scalar(
        select(func.count()).select_from(SimilarityPair).where(SimilarityPair.status == "recommended")
    ) or 0
    completed = db.scalar(
        select(func.count()).select_from(IngestJob).where(IngestJob.status == "completed")
    ) or 0
    sensitive = db.scalar(
        select(func.count()).select_from(SemanticTag).where(SemanticTag.tag_name.like("sensitive:%"))
    ) or 0
    inferred = db.scalar(
        select(func.count()).select_from(AssetColumn).where(AssetColumn.inferred_type.is_not(None))
    ) or 0
    return {
        "assets": count(Asset),
        "columns": count(AssetColumn),
        "inferred_columns": inferred,
        "semantic_tags": count(SemanticTag),
        "sensitive_columns": sensitive,
        "similarity_pairs": count(SimilarityPair),
        "pending_pairs": pending_pairs,
        "ingest_jobs": count(IngestJob),
        "completed_jobs": completed,
        "roles": ["admin", "analyst", "viewer"],
    }


def audit_logs(db: Session, limit: int) -> dict:
    from src.services import audit_service

    return {"items": audit_service.list_logs(db, limit=limit)}
