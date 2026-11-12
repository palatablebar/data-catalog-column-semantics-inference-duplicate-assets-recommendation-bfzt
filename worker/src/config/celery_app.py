"""worker Celery 应用：消费 backend 投递的任务，并跑 beat 心跳。"""
from __future__ import annotations

from celery import Celery
from celery.schedules import schedule

from worker_src.config.settings import settings

celery_app = Celery(
    "catmap_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "worker_src.tasks.ingest_task",
        "worker_src.tasks.heartbeat_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_acks_late=False,
)

celery_app.conf.beat_schedule = {
    "worker-heartbeat": {
        "task": "catmap.heartbeat",
        "schedule": schedule(run_every=10),
    },
}
