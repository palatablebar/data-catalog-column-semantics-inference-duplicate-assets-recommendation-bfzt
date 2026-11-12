from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import duplicate_controller
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.duplicate import DismissRequest, RecomputeRequest

router = APIRouter(prefix="/duplicates", tags=["duplicates"])


@router.post("/recompute")
def recompute(
    payload: RecomputeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("duplicate:recompute")),
    _: User = rate_limit("recompute"),
) -> dict:
    return duplicate_controller.recompute(db, user, payload.top_n, payload.min_score)


@router.get("")
def list_pairs(
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("duplicate:read")),
) -> dict:
    return duplicate_controller.list_pairs(db, limit)


@router.get("/{pair_id}")
def detail(
    pair_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("duplicate:read")),
) -> dict:
    return duplicate_controller.detail(db, pair_id)


@router.post("/{pair_id}/merge-suggestion")
def merge_suggestion(
    pair_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("duplicate:merge")),
    _: User = rate_limit("merge"),
) -> dict:
    return duplicate_controller.merge_suggestion(db, pair_id, user)


@router.post("/{pair_id}/dismiss")
def dismiss(
    pair_id: str,
    payload: DismissRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("duplicate:dismiss")),
    _: User = rate_limit("dismiss"),
) -> dict:
    return duplicate_controller.dismiss(db, pair_id, payload.note, user)
