from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import meta_controller
from src.middlewares.rbac import require_permission
from src.models.user import User

router = APIRouter(tags=["meta"])


@router.get("/meta/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(require_permission("asset:read"))) -> dict:
    return meta_controller.overview(db)


@router.get("/audit")
def audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("audit:read")),
) -> dict:
    return meta_controller.audit_logs(db, limit)
