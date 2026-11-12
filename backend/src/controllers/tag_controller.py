"""语义标签控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.user import User
from src.services import audit_service, tag_service


def list_tags(db: Session, **filters) -> dict:
    return tag_service.list_tags(db, **filters)


def create(db: Session, payload, user: User) -> dict:
    result = tag_service.create_tag(db, payload=payload, actor=user)
    audit_service.record(
        db,
        actor_email=user.email,
        actor_role=user.role,
        action="tag.create",
        entity_type="semantic_tag",
        entity_id=result["column_id"],
        detail=f"{payload.tag_name} on column={payload.column_id}",
    )
    return result


def bulk(db: Session, payload, user: User) -> dict:
    result = tag_service.bulk_tag(db, payload=payload, actor=user)
    audit_service.record(
        db,
        actor_email=user.email,
        actor_role=user.role,
        action="tag.bulk",
        entity_type="semantic_tag",
        detail=f"{payload.tag_name} on {result['total']} columns",
    )
    return result


def delete(db: Session, tag_id: str, user: User) -> dict:
    result = tag_service.delete_tag(db, tag_id)
    audit_service.record(
        db,
        actor_email=user.email,
        actor_role=user.role,
        action="tag.delete",
        entity_type="semantic_tag",
        entity_id=tag_id,
    )
    return result
