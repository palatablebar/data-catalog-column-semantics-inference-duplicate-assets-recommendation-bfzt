from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import ingest_controller
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.models.user import User
from src.schemas.ingest import CreateJobRequest

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(require_permission("ingest:read"))) -> dict:
    return ingest_controller.overview(db)


@router.get("/jobs")
def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("ingest:read")),
) -> dict:
    return ingest_controller.list_jobs(db, limit)


@router.post("/jobs")
def create(
    payload: CreateJobRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("ingest:run")),
    _: User = rate_limit("ingest"),
) -> dict:
    return ingest_controller.create(db, payload, user)


@router.get("/jobs/{job_id}")
def detail(
    job_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("ingest:read")),
) -> dict:
    return ingest_controller.detail(db, job_id)
