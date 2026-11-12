from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import tag_controller
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.tag import BulkTagRequest, CreateTagRequest

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("")
def list_tags(
    category: str | None = None,
    source: str | None = None,
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("tag:read")),
) -> dict:
    return tag_controller.list_tags(db, category=category, source=source, q=q)


@router.post("")
def create(
    payload: CreateTagRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("tag:write")),
    _: User = rate_limit("tag"),
) -> dict:
    return tag_controller.create(db, payload, user)


@router.post("/bulk")
def bulk(
    payload: BulkTagRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("tag:write")),
    _: User = rate_limit("tag"),
) -> dict:
    return tag_controller.bulk(db, payload, user)


@router.delete("/{tag_id}")
def delete(
    tag_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("asset:write")),
    _: User = rate_limit("tag"),
) -> dict:
    return tag_controller.delete(db, tag_id, user)
