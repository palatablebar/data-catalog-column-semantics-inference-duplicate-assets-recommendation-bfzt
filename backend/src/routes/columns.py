from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import column_controller
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.column import CorrectTypeRequest

router = APIRouter(prefix="/columns", tags=["columns"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), _: User = Depends(require_permission("column:read"))) -> dict:
    return column_controller.summary(db)


@router.post("/infer")
def infer(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("column:infer")),
    _: User = rate_limit("infer"),
) -> dict:
    return column_controller.infer(db, user)


@router.get("")
def list_columns(
    inferred_type: str | None = None,
    layer: str | None = None,
    q: str | None = None,
    only_profiled: bool = True,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("column:read")),
) -> dict:
    return column_controller.list_columns(
        db,
        inferred_type=inferred_type,
        layer=layer,
        q=q,
        only_profiled=only_profiled,
        page=page,
        page_size=page_size,
    )


@router.get("/{column_id}")
def detail(
    column_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("column:read")),
) -> dict:
    return column_controller.detail(db, column_id)


@router.patch("/{column_id}/type")
def correct_type(
    column_id: str,
    payload: CorrectTypeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("column:correct")),
    _: User = rate_limit("correct"),
) -> dict:
    return column_controller.correct(db, column_id, payload.inferred_type, payload.note, user)
