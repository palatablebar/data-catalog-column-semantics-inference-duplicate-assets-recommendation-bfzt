"""采集任务服务：建任务 → Celery 投递 → worker 读样例表统计 → 任务结果。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.config.celery_app import dispatch_task
from src.constants import error_codes as codes
from src.constants.enums import IngestJobStatus, InferenceSource
from src.constants.tasks import TASK_RUN_INGEST
from src.models.asset import Asset
from src.models.asset_column import AssetColumn
from src.models.ingest_job import IngestJob
from src.models.user import User
from src.schemas.common import iso
from src.services import audit_service
from src.utils.errors import AppError


def job_payload(job: IngestJob) -> dict:
    return {
        "id": str(job.id),
        "job_name": job.job_name,
        "connection_name": job.connection_name,
        "scope": job.scope,
        "status": job.status,
        "stats": job.stats or {},
        "error_code": job.error_code,
        "error_message": job.error_message,
        "triggered_by": job.triggered_by,
        "started_at": iso(job.started_at),
        "finished_at": iso(job.finished_at),
        "created_at": iso(job.created_at),
    }


def list_jobs(db: Session, limit: int = 20) -> dict:
    jobs = db.scalars(
        select(IngestJob).order_by(IngestJob.created_at.desc()).limit(limit)
    ).all()
    all_jobs = db.scalars(select(IngestJob)).all()
    counts: dict[str, int] = {}
    for job in all_jobs:
        counts[job.status] = counts.get(job.status, 0) + 1
    return {"items": [job_payload(job) for job in jobs], "total": len(all_jobs), "counts": counts}


def get_job(db: Session, job_id: str) -> dict:
    job = db.get(IngestJob, job_id)
    if job is None:
        raise AppError(codes.NOT_FOUND, "采集任务不存在", f"job_id={job_id}")
    return job_payload(job)


def create_job(db: Session, *, job_name: str, connection_name: str, scope: str, actor: User) -> dict:
    job = IngestJob(
        job_name=job_name,
        connection_name=connection_name,
        scope=scope,
        status=IngestJobStatus.QUEUED.value,
        triggered_by=actor.email,
        stats={"tables_synced": 0},
    )
    db.add(job)
    db.flush()

    dispatched = dispatch_task(TASK_RUN_INGEST, [str(job.id)])
    if not dispatched:
        job.status = IngestJobStatus.FAILED.value
        job.error_code = codes.WORKER_UNAVAILABLE
        job.error_message = "Celery 投递失败：采集执行器不可用"
        job.finished_at = datetime.now(timezone.utc)
    audit_service.record(
        db,
        actor_email=actor.email,
        actor_role=actor.role,
        action="ingest.run",
        entity_type="ingest_job",
        entity_id=str(job.id),
        detail=f"{job.job_name} scope={job.scope} dispatched={dispatched}",
    )
    db.flush()
    return job_payload(job)


def overview(db: Session) -> dict:
    total_columns = db.scalar(select(func.count()).select_from(AssetColumn)) or 0
    profiled_columns = (
        db.scalar(
            select(func.count()).select_from(AssetColumn).where(AssetColumn.stats.is_not(None))
        )
        or 0
    )
    sample_assets = (
        db.scalar(
            select(func.count()).select_from(Asset).where(Asset.source_kind == "sample_table")
        )
        or 0
    )
    last_completed = db.scalars(
        select(IngestJob)
        .where(IngestJob.status == IngestJobStatus.COMPLETED.value)
        .order_by(IngestJob.finished_at.desc())
        .limit(1)
    ).first()
    manual_columns = (
        db.scalar(
            select(func.count())
            .select_from(AssetColumn)
            .where(AssetColumn.inference_source == InferenceSource.MANUAL.value)
        )
        or 0
    )
    jobs = db.scalars(select(IngestJob)).all()
    return {
        "total_columns": total_columns,
        "profiled_columns": profiled_columns,
        "coverage": round(profiled_columns / total_columns, 3) if total_columns else 0.0,
        "sample_assets": sample_assets,
        "manual_columns": manual_columns,
        "jobs": {
            status.value: sum(1 for job in jobs if job.status == status.value)
            for status in IngestJobStatus
        },
        "last_completed": job_payload(last_completed) if last_completed else None,
    }
