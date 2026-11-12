"""语义标签服务：列表 / 创建 / 批量打标 / 删除，打标写审计。"""
from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import TagSource
from src.models.asset import Asset
from src.models.asset_column import AssetColumn
from src.models.semantic_tag import SemanticTag
from src.models.user import User
from src.schemas.common import iso, tag_payload
from src.utils.errors import AppError

VALID_CATEGORIES = {"pii", "business", "governance"}
SENSITIVE_PREFIX = "sensitive:"


def tags_by_asset(db: Session, asset_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """{asset_id: {column_id: [tag payload]}}，列表接口一次查明细标签，避免 N+1。"""
    if not asset_ids:
        return {}
    rows = db.execute(
        select(SemanticTag, AssetColumn.asset_id)
        .join(AssetColumn, AssetColumn.id == SemanticTag.asset_column_id)
        .where(AssetColumn.asset_id.in_(asset_ids))
    ).all()
    result: dict[uuid.UUID, dict] = defaultdict(dict)
    for tag, asset_id in rows:
        result[asset_id].setdefault(tag.asset_column_id, []).append(tag_payload(tag))
    return result


def tags_for_column(db: Session, column_id: uuid.UUID) -> list[dict]:
    tags = db.scalars(select(SemanticTag).where(SemanticTag.asset_column_id == column_id)).all()
    return [tag_payload(tag) for tag in tags]


def list_tags(db: Session, *, category: str | None = None, source: str | None = None, q: str | None = None) -> dict:
    query = (
        select(SemanticTag, AssetColumn, Asset)
        .join(AssetColumn, AssetColumn.id == SemanticTag.asset_column_id)
        .join(Asset, Asset.id == AssetColumn.asset_id)
    )
    if category:
        query = query.where(SemanticTag.category == category)
    if source:
        query = query.where(SemanticTag.source == source)
    if q:
        query = query.where(SemanticTag.tag_name.like(f"%{q.strip()}%"))
    rows = db.execute(query.order_by(SemanticTag.tag_name, Asset.asset_key)).all()
    items = []
    for tag, column, asset in rows:
        items.append(
            {
                **tag_payload(tag),
                "column": {
                    "id": str(column.id),
                    "column_name": column.column_name,
                    "data_type": column.data_type,
                    "inferred_type": column.inferred_type,
                    "confidence": round(column.confidence or 0.0, 3),
                },
                "asset": {
                    "id": str(asset.id),
                    "asset_key": asset.asset_key,
                    "table_name": asset.table_name,
                    "layer": asset.layer,
                    "domain": asset.domain,
                },
            }
        )
    by_category: dict[str, int] = defaultdict(int)
    by_source: dict[str, int] = defaultdict(int)
    sensitive = 0
    for item in items:
        by_category[item["category"]] += 1
        by_source[item["source"]] += 1
        if item["tag_name"].startswith(SENSITIVE_PREFIX):
            sensitive += 1
    return {
        "items": items,
        "total": len(items),
        "summary": {
            "by_category": dict(by_category),
            "by_source": dict(by_source),
            "sensitive_columns": sensitive,
        },
    }


def upsert_tag(
    db: Session,
    *,
    column: AssetColumn,
    tag_name: str,
    category: str,
    actor: User,
    confidence: float = 1.0,
    source: str = TagSource.MANUAL.value,
) -> tuple[SemanticTag, bool]:
    if category not in VALID_CATEGORIES:
        raise AppError(codes.VALIDATION_ERROR, f"分类必须是 {sorted(VALID_CATEGORIES)} 之一", category)
    cleaned = tag_name.strip().lower()
    if len(cleaned) < 2:
        raise AppError(codes.VALIDATION_ERROR, "标签名过短", tag_name)
    existing = db.scalars(
        select(SemanticTag).where(
            SemanticTag.asset_column_id == column.id, SemanticTag.tag_name == cleaned
        )
    ).first()
    created = existing is None
    if existing is None:
        existing = SemanticTag(
            asset_column_id=column.id,
            tag_name=cleaned,
            category=category,
            source=source,
            confidence=confidence,
            tagged_by=actor.email,
        )
        db.add(existing)
    else:
        existing.category = category
        existing.source = source
        existing.confidence = confidence
        existing.tagged_by = actor.email
    db.flush()
    return existing, created


def create_tag(db: Session, *, payload, actor: User) -> dict:
    column = db.get(AssetColumn, payload.column_id)
    if column is None:
        raise AppError(codes.NOT_FOUND, "列不存在", f"column_id={payload.column_id}")
    tag, created = upsert_tag(
        db,
        column=column,
        tag_name=payload.tag_name,
        category=payload.category,
        actor=actor,
        confidence=payload.confidence,
    )
    return {"created": created, "tag": tag_payload(tag), "column_id": str(column.id)}


def bulk_tag(db: Session, *, payload, actor: User) -> dict:
    created = 0
    updated = 0
    for column_id in payload.column_ids:
        try:
            column = db.get(AssetColumn, column_id)
        except Exception as exc:  # noqa: BLE001 - 非法 UUID 视为参数错误
            raise AppError(codes.VALIDATION_ERROR, "列 ID 不合法", str(exc)) from exc
        if column is None:
            raise AppError(codes.NOT_FOUND, "列不存在", f"column_id={column_id}")
        _, is_created = upsert_tag(
            db,
            column=column,
            tag_name=payload.tag_name,
            category=payload.category,
            actor=actor,
            confidence=1.0,
        )
        if is_created:
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated, "total": len(payload.column_ids)}


def delete_tag(db: Session, tag_id: str) -> dict:
    tag = db.get(SemanticTag, tag_id)
    if tag is None:
        raise AppError(codes.NOT_FOUND, "标签不存在", f"tag_id={tag_id}")
    db.delete(tag)
    return {"deleted": True, "tag_id": tag_id}
