"""worker 心跳：写 Redis 键，供容器 healthcheck 判断执行器存活。"""
from __future__ import annotations

import time

import redis

from worker_src.config.celery_app import celery_app
from worker_src.config.settings import settings


@celery_app.task(name="catmap.heartbeat")
def heartbeat() -> dict:
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
    client.set("catmap:worker:heartbeat", str(time.time()), ex=120)
    return {"ok": True, "ts": time.time()}
