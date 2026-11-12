"""采集任务控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.user import User
from src.services import ingest_service


def list_jobs(db: Session, limit: int = 20) -> dict:
    return ingest_service.list_jobs(db, limit=limit)


def create(db: Session, payload, user: User) -> dict:
    return ingest_service.create_job(
        db,
        job_name=payload.job_name,
        connection_name=payload.connection_name,
        scope=payload.scope,
        actor=user,
    )


def detail(db: Session, job_id: str) -> dict:
    return ingest_service.get_job(db, job_id)


def overview(db: Session) -> dict:
    return ingest_service.overview(db)
