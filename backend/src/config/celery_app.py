"""Celery 入口：backend 只投递任务，真正消费在 worker 容器。"""
from __future__ import annotations

from celery import Celery

from src.config.settings import settings
from src.constants.tasks import TASK_RUN_INGEST  # noqa: F401

celery_app = Celery(
    "catmap",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)


def dispatch_task(name: str, args: list | None = None) -> bool:
    """投递任务；broker 不可用时返回 False，让控制层能降级成 failed 而不是 500。"""
    try:
        celery_app.send_task(name, args=args or [])
        return True
    except Exception:  # noqa: BLE001 - 投递失败由 controller 标记 job failed
        return False
