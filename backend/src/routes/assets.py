from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import asset_controller
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.models.user import User

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/facets")
def facets(db: Session = Depends(get_db), _: User = Depends(require_permission("asset:read"))) -> dict:
    return asset_controller.facets(db)


@router.get("/export.csv")
def export_csv(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("export:run")),
    __: User = rate_limit("export"),
) -> Response:
    filename, content = asset_controller.export_csv(db)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("")
def list_assets(
    layer: str | None = None,
    domain: str | None = None,
    q: str | None = None,
    source_kind: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("asset:read")),
) -> dict:
    return asset_controller.list_assets(
        db,
        layer=layer,
        domain=domain,
        q=q,
        source_kind=source_kind,
        page=page,
        page_size=page_size,
    )


@router.get("/{asset_id}")
def detail(
    asset_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("asset:read")),
) -> dict:
    return asset_controller.detail(db, asset_id)
