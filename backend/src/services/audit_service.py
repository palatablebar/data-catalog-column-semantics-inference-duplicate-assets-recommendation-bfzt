"""审计日志服务：关键写动作 + 越权尝试落 audit_log 表。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog


def record(
    db: Session,
    *,
    actor_email: str,
    actor_role: str,
    action: str,
    entity_type: str,
    entity_id: str = "",
    detail: str = "",
    trace_id: str = "",
) -> None:
    db.add(
        AuditLog(
            actor_email=actor_email,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id)[:80],
            detail=detail[:500],
            trace_id=trace_id[:40],
        )
    )


def list_logs(db: Session, limit: int = 50) -> list[dict]:
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [
        {
            "id": str(row.id),
            "actor_email": row.actor_email,
            "actor_role": row.actor_role,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "detail": row.detail,
            "trace_id": row.trace_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
