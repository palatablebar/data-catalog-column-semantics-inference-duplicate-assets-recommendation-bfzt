"""列语义推断服务（算法 A 的落库层）：
- infer_all：读 asset_column.stats 里的采样值 → typing_engine 真算 → 写回类型/置信度/证据
- correct_type：人工纠正（source=manual，写审计）
"""
from __future__ import annotations

from collections import Counter

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.enums import ColumnSemanticType, InferenceSource, TYPABLE_TYPES
from src.models.asset import Asset
from src.models.asset_column import AssetColumn
from src.models.user import User
from src.schemas.common import asset_brief, iso, tag_payload
from src.services import audit_service, tag_service, typing_engine
from src.utils.errors import AppError


def _column_item(column: AssetColumn, asset: Asset, tags: list[dict]) -> dict:
    stats = column.stats or {}
    return {
        "id": str(column.id),
        "column_name": column.column_name,
        "data_type": column.data_type,
        "inferred_type": column.inferred_type,
        "confidence": round(column.confidence or 0.0, 3),
        "inference_source": column.inference_source,
        "evidence": column.evidence or [],
        "candidates": column.candidates or [],
        "sample_values": (column.sample_values or [])[:5],
        "profiled": bool(column.stats),
        "stats": {
            "sample_count": stats.get("sample_count", 0),
            "null_rate": stats.get("null_rate", 0.0),
            "unique_count": stats.get("unique_count", 0),
            "profile_source": stats.get("profile_source", ""),
        },
        "asset": asset_brief(asset),
        "tags": tags,
    }


def infer_all(db: Session, actor: User) -> dict:
    """对已有采样统计的列做批量语义推断（结果落 asset_column，前端只读）。"""
    columns = db.scalars(
        select(AssetColumn)
        .options(selectinload(AssetColumn.asset))
        .where(AssetColumn.stats.is_not(None))
        .order_by(AssetColumn.asset_id, AssetColumn.ordinal)
    ).all()
    if not columns:
        raise AppError(
            codes.CONFLICT,
            "还没有任何列统计，请先运行采集任务",
            "asset_column.stats 全为空",
        )

    by_type: Counter[str] = Counter()
    updated = 0
    for column in columns:
        samples = column.sample_values or []
        result = typing_engine.infer_column(
            column.column_name,
            samples,
            data_type=column.data_type,
            sample_limit=settings.inference_sample_limit,
        )
        # 人工纠正过的列不被算法覆盖（保留 manual 来源）
        if column.inference_source == InferenceSource.MANUAL.value:
            by_type[column.inferred_type or ColumnSemanticType.UNKNOWN.value] += 1
            continue
        column.inferred_type = result["inferred_type"]
        column.confidence = result["confidence"]
        column.inference_source = InferenceSource.AUTO.value
        column.evidence = result["evidence"]
        column.candidates = result["candidates"]
        stats = dict(column.stats or {})
        stats["features"] = result["features"]
        column.stats = stats
        by_type[result["inferred_type"]] += 1
        updated += 1

    audit_service.record(
        db,
        actor_email=actor.email,
        actor_role=actor.role,
        action="column.infer",
        entity_type="asset_column",
        detail=f"推断 {updated} 列，phone={by_type.get('phone', 0)} email={by_type.get('email', 0)} "
        f"id_card={by_type.get('id_card', 0)}",
    )
    return {
        "processed": len(columns),
        "updated": updated,
        "by_type": dict(by_type),
        "human_corrected": sum(
            1 for column in columns if column.inference_source == InferenceSource.MANUAL.value
        ),
    }


def infer_summary(db: Session) -> dict:
    rows = db.execute(
        select(AssetColumn.inferred_type, func.count())
        .where(AssetColumn.inferred_type.is_not(None))
        .group_by(AssetColumn.inferred_type)
    ).all()
    by_type = {key: count for key, count in rows}
    total_columns = db.scalar(select(func.count()).select_from(AssetColumn)) or 0
    profiled = db.scalar(
        select(func.count()).select_from(AssetColumn).where(AssetColumn.stats.is_not(None))
    ) or 0
    manual = db.scalar(
        select(func.count())
        .select_from(AssetColumn)
        .where(AssetColumn.inference_source == InferenceSource.MANUAL.value)
    ) or 0
    unknown = by_type.get(ColumnSemanticType.UNKNOWN.value, 0)
    ambiguous = by_type.get(ColumnSemanticType.AMBIGUOUS.value, 0)
    inferred_total = sum(by_type.values())
    return {
        "total_columns": total_columns,
        "inferred_columns": inferred_total,
        "not_inferred_columns": total_columns - inferred_total,
        "profiled_columns": profiled,
        "by_type": by_type,
        "unknown_columns": unknown,
        "ambiguous_columns": ambiguous,
        "human_corrected": manual,
        "type_labels": {key: key for key in by_type},
    }


def list_columns(
    db: Session,
    *,
    inferred_type: str | None = None,
    layer: str | None = None,
    q: str | None = None,
    only_profiled: bool = True,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    from src.utils.pagination import page_payload, parse_page

    query = (
        select(AssetColumn)
        .join(Asset, Asset.id == AssetColumn.asset_id)
        .options(selectinload(AssetColumn.asset))
    )
    count_query = select(func.count()).select_from(AssetColumn).join(
        Asset, Asset.id == AssetColumn.asset_id
    )
    conditions = []
    if inferred_type:
        if inferred_type == "typed":
            conditions.append(AssetColumn.inferred_type.in_([item.value for item in TYPABLE_TYPES]))
        else:
            conditions.append(AssetColumn.inferred_type == inferred_type)
    if only_profiled:
        conditions.append(AssetColumn.stats.is_not(None))
    if layer:
        conditions.append(Asset.layer == layer)
    if q:
        keyword = f"%{q.strip().lower()}%"
        conditions.append(
            or_(
                func.lower(AssetColumn.column_name).like(keyword),
                func.lower(Asset.asset_key).like(keyword),
            )
        )
    for condition in conditions:
        query = query.where(condition)
        count_query = count_query.where(condition)

    pagination = parse_page(page, page_size)
    total = db.scalar(count_query) or 0
    columns = db.scalars(
        query.order_by(AssetColumn.confidence.desc(), Asset.asset_key, AssetColumn.ordinal)
        .offset(pagination.offset)
        .limit(pagination.limit)
    ).all()

    asset_ids = {column.asset_id for column in columns}
    tag_map = tag_service.tags_by_asset(db, list(asset_ids))
    items = []
    for column in columns:
        tags = tag_map.get(column.asset_id, {}).get(column.id, [])
        items.append(_column_item(column, column.asset, tags))
    return page_payload(pagination, total, items)


def get_column(db: Session, column_id: str) -> dict:
    column = db.scalars(
        select(AssetColumn)
        .options(selectinload(AssetColumn.asset))
        .where(AssetColumn.id == column_id)
    ).first()
    if column is None:
        raise AppError(codes.NOT_FOUND, "列不存在", f"column_id={column_id}")
    tags = tag_service.tags_for_column(db, column.id)
    return {
        **_column_item(column, column.asset, tags),
        "evidence": column.evidence or [],
        "candidates": column.candidates or [],
        "profiled_at": iso(column.profiled_at),
    }


def correct_type(db: Session, column_id: str, inferred_type: str, note: str, actor: User) -> dict:
    if inferred_type not in {item.value for item in list(ColumnSemanticType)}:
        raise AppError(
            codes.VALIDATION_ERROR,
            f"不支持的列语义类型：{inferred_type}",
            "allowed=" + ",".join(item.value for item in ColumnSemanticType),
        )
    column = db.scalars(
        select(AssetColumn)
        .options(selectinload(AssetColumn.asset))
        .where(AssetColumn.id == column_id)
    ).first()
    if column is None:
        raise AppError(codes.NOT_FOUND, "列不存在", f"column_id={column_id}")

    previous = column.inferred_type
    evidence = list(column.evidence or [])
    evidence.append(
        f"人工纠正：{previous or 'unknown'} → {inferred_type}，操作人 {actor.email}"
        + (f"，备注：{note}" if note else "")
    )
    column.inferred_type = inferred_type
    column.confidence = 1.0
    column.inference_source = InferenceSource.MANUAL.value
    column.evidence = evidence[-12:]

    audit_service.record(
        db,
        actor_email=actor.email,
        actor_role=actor.role,
        action="column.correct_type",
        entity_type="asset_column",
        entity_id=str(column.id),
        detail=f"{column.asset.asset_key}.{column.column_name}: {previous} → {inferred_type}",
    )
    return {
        "column": _column_item(column, column.asset, tag_service.tags_for_column(db, column.id)),
        "previous_type": previous,
        "inference_source": column.inference_source,
    }
