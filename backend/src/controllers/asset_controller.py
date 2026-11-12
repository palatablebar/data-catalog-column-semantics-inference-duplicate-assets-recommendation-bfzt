"""资产控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.services import asset_service, export_service


def facets(db: Session) -> dict:
    return asset_service.facets(db)


def list_assets(db: Session, **filters) -> dict:
    return asset_service.list_assets(db, **filters)


def detail(db: Session, asset_id: str) -> dict:
    return asset_service.get_asset(db, asset_id)


def export_csv(db: Session) -> tuple[str, bytes]:
    return export_service.build_catalog_csv(db)
