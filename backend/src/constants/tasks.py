"""跨容器共享的 Celery 任务名。"""
from __future__ import annotations

TASK_RUN_INGEST = "catmap.run_ingest"
TASK_HEARTBEAT = "catmap.heartbeat"
TASK_RECOMPUTE_SIMILARITY = "catmap.recompute_similarity"
