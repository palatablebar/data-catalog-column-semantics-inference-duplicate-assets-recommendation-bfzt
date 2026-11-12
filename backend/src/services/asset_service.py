"""资产检索服务：左树 facets / 列表 / 详情 / 导出。"""
from __future__ import annotations

from collections import Counter

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from src.constants.enums import AssetLayer, AssetSourceKind
from src.constants.roles import Role
from src.models.asset import Asset
from src.models.asset_column import AssetColumn
from src.models.semantic_tag import SemanticTag
from src.schemas.common import asset_brief, column_brief, iso, tag_payload
from src.services import tag_service
from src.utils.pagination import Page, page_payload, parse_page


def _base_query():
    return select(Asset).options(selectinload(Asset.columns))


def facets(db: Session) -> dict:
    assets = db.scalars(select(Asset)).all()
    layer_counts = Counter(asset.layer for asset in assets)
    domain_counts = Counter(asset.domain for asset in assets)
    sample_tables = sum(1 for asset in assets if asset.source_kind == AssetSourceKind.SAMPLE_TABLE)
    profiled = db.scalar(
        select(func.count()).select_from(AssetColumn).where(AssetColumn.stats.is_not(None))
    )
    total_columns = db.scalar(select(func.count()).select_from(AssetColumn))
    sensitive = db.scalar(
        select(func.count()).select_from(SemanticTag).where(SemanticTag.tag_name.like("sensitive:%"))
    )
    return {
        "layers": [
            {"value": layer.value, "label": layer.value.upper(), "count": layer_counts.get(layer.value, 0)}
            for layer in AssetLayer
        ],
        "domains": [
            {"value": value, "count": count}
            for value, count in sorted(domain_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "stats": {
            "assets": len(assets),
            "sample_tables": sample_tables,
            "metadata_only": len(assets) - sample_tables,
            "columns": total_columns or 0,
            "profiled_columns": profiled or 0,
            "sensitive_columns": sensitive or 0,
        },
    }


def list_assets(
    db: Session,
    *,
    layer: str | None = None,
    domain: str | None = None,
    q: str | None = None,
    source_kind: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = _base_query()
    count_query = select(func.count()).select_from(Asset)
    filters = []
    if layer:
        filters.append(Asset.layer == layer)
    if domain:
        filters.append(Asset.domain == domain)
    if source_kind:
        filters.append(Asset.source_kind == source_kind)
    if q:
        keyword = f"%{q.strip().lower()}%"
        filters.append(
            or_(
                func.lower(Asset.table_name).like(keyword),
                func.lower(Asset.asset_key).like(keyword),
                func.lower(Asset.description).like(keyword),
                func.lower(Asset.domain).like(keyword),
            )
        )
    for condition in filters:
        query = query.where(condition)
        count_query = count_query.where(condition)

    pagination: Page = parse_page(page, page_size)
    total = db.scalar(count_query) or 0
    assets = db.scalars(
        query.order_by(Asset.layer, Asset.table_name).offset(pagination.offset).limit(pagination.limit)
    ).all()

    tag_map = tag_service.tags_by_asset(db, [asset.id for asset in assets])
    items = []
    for asset in assets:
        column_tags = tag_map.get(asset.id, {})
        columns = [
            {
                **column_brief(column),
                "tags": column_tags.get(column.id, []),
            }
            for column in asset.columns[:6]
        ]
        sensitive_count = sum(
            1 for tags in column_tags.values() if any(tag["tag_name"].startswith("sensitive:") for tag in tags)
        )
        items.append(
            {
                **asset_brief(asset),
                "description": asset.description,
                "owner_name": asset.owner_name,
                "source_kind": asset.source_kind,
                "is_active": asset.is_active,
                "updated_at": iso(asset.updated_at),
                "sensitive_tag_count": sensitive_count,
                "typed_column_count": sum(1 for column in asset.columns if column.inferred_type),
                "columns_preview": columns,
            }
        )
    return page_payload(pagination, total, items)


def get_asset(db: Session, asset_id: str) -> dict:
    asset = db.scalars(_base_query().where(Asset.id == asset_id)).first()
    if asset is None:
        from src.constants import error_codes as codes
        from src.utils.errors import AppError

        raise AppError(codes.NOT_FOUND, "资产不存在", f"asset_id={asset_id}")
    tag_map = tag_service.tags_by_asset(db, [asset.id])
    column_tags = tag_map.get(asset.id, {})
    columns = []
    for column in asset.columns:
        columns.append(
            {
                **column_brief(column),
                "ordinal": column.ordinal,
                "nullable": column.nullable,
                "comment": column.comment,
                "evidence": column.evidence or [],
                "candidates": column.candidates or [],
                "sample_values": (column.sample_values or [])[:8],
                "stats": column.stats or {},
                "tags": column_tags.get(column.id, []),
            }
        )
    return {
        **asset_brief(asset),
        "description": asset.description,
        "owner_name": asset.owner_name,
        "source_kind": asset.source_kind,
        "is_active": asset.is_active,
        "updated_at": iso(asset.updated_at),
        "columns": columns,
        "sensitive_tag_count": sum(
            1
            for column in columns
            if any(tag["tag_name"].startswith("sensitive:") for tag in column["tags"])
        ),
    }


def export_rows(db: Session) -> list[list[str]]:
    """目录 CSV：资产 + 列级推断 + 敏感标签，供 viewer 导出复核。"""
    assets = db.scalars(_base_query().order_by(Asset.layer, Asset.table_name)).all()
    tag_map = tag_service.tags_by_asset(db, [asset.id for asset in assets])
    rows: list[list[str]] = []
    for asset in assets:
        column_tags = tag_map.get(asset.id, {})
        if not asset.columns:
            rows.append(
                [
                    asset.asset_key,
                    asset.layer,
                    asset.domain,
                    asset.owner_name,
                    asset.source_kind,
                    str(asset.row_count),
                    "",
                    "",
                    "",
                    "",
                ]
            )
            continue
        for column in asset.columns:
            tags = column_tags.get(column.id, [])
            rows.append(
                [
                    asset.asset_key,
                    asset.layer,
                    asset.domain,
                    asset.owner_name,
                    asset.source_kind,
                    str(asset.row_count),
                    column.column_name,
                    column.data_type,
                    column.inferred_type or "",
                    "; ".join(tag["tag_name"] for tag in tags),
                ]
            )
    return rows


def layer_export_header() -> list[str]:
    return ["asset_key", "layer", "domain", "owner", "source_kind", "row_count", "column_name",
            "data_type", "inferred_type", "tags"]
