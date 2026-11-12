"""采集任务：读 5 张样例表 → 逐列统计 + 200 个抽样值 → 写 asset / asset_column。"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text

from src.config.database import session_scope
from src.models.asset import Asset
from src.models.asset_column import AssetColumn
from src.models.ingest_job import IngestJob
from src.utils.logger import get_logger
from worker_src.config.celery_app import celery_app
from worker_src.config.settings import settings
from worker_src.core import sampler

logger = get_logger("catmap.worker.ingest")


@celery_app.task(bind=True, name="catmap.run_ingest", max_retries=0)
def run_ingest(self, job_id: str) -> dict:  # noqa: ARG001
    started = time.perf_counter()
    with session_scope() as db:
        job = db.get(IngestJob, uuid.UUID(str(job_id)))
        if job is None:
            logger.warning("ingest job not found job=%s", job_id)
            return {"ok": False, "reason": "job_not_found"}
        if job.status in ("completed", "running"):
            return {"ok": False, "reason": f"job_status={job.status}"}

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db.flush()

        try:
            stats = _profile_sample_tables(db)
        except Exception as exc:  # noqa: BLE001
            logger.error("ingest failed job=%s error=%s", job_id, exc, exc_info=True)
            job.status = "failed"
            job.error_code = "profile_failed"
            job.error_message = str(exc)[:255]
            job.finished_at = datetime.now(timezone.utc)
            db.flush()
            return {"ok": False, "reason": "profile_failed", "error": str(exc)}

        duration_ms = int((time.perf_counter() - started) * 1000)
        job.status = "completed"
        job.stats = {**stats, "duration_ms": duration_ms}
        job.finished_at = datetime.now(timezone.utc)
        db.flush()
        logger.info("ingest completed job=%s stats=%s", job_id, stats)
        return {"ok": True, "job_id": str(job.id), "stats": job.stats}


def _profile_sample_tables(db) -> dict:
    schema = settings.sample_schema
    assets = db.scalars(
        select(Asset).where(Asset.source_kind == "sample_table").order_by(Asset.table_name)
    ).all()
    tables_synced = 0
    rows_scanned = 0
    columns_profiled = 0
    connection = db.connection()
    for asset in assets:
        table = asset.table_name
        try:
            row_count = sampler.table_row_count(connection, schema, table)
        except Exception as exc:  # noqa: BLE001 - 缺表只跳过该资产
            logger.warning("sample table missing table=%s error=%s", table, exc)
            continue
        columns = db.scalars(
            select(AssetColumn)
            .where(AssetColumn.asset_id == asset.id)
            .order_by(AssetColumn.ordinal)
        ).all()
        for column in columns:
            profile = sampler.profile_column(connection, schema, table, column.column_name)
            stats = dict(column.stats or {})
            stats.update(profile["stats"])
            column.stats = stats
            column.sample_values = profile["sample_values"]
            column.profiled_at = datetime.now(timezone.utc)
        asset.row_count = row_count
        asset.column_count = len(columns)
        asset.updated_at = datetime.now(timezone.utc)
        tables_synced += 1
        rows_scanned += row_count
        columns_profiled += len(columns)
    db.flush()
    return {
        "tables_synced": tables_synced,
        "rows_scanned": rows_scanned,
        "columns_profiled": columns_profiled,
        "sample_schema": schema,
        "mode": "sample_profile",
    }
