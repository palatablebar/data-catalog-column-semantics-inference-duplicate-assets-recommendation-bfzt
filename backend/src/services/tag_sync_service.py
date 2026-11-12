"""敏感标签同步服务：把人工确认的敏感结论沿相似表对的匹配列做预览与应用。

业务规则（与评审口径一致）：
  ① 只传播 source=manual 且 tag_name 以 ``sensitive:`` 开头的人工敏感结论，
     inferred 标签不参与，避免把算法猜测继续扩散。
  ② 匹配列复用相似度引擎的列名归一化结果（suggestion.merged_columns，缺失则现场重算）。
  ③ 目标列已有判断的保留原结论：
       - 已存在同名标签            → skipped(reason=tag_exists)
       - 已存在任意 sensitive 标签 → skipped(reason=sensitive_exists)
       - 仅有非敏感标签            → 仍可补标（不算已有敏感判断）
  ④ 两列推断语义类型都明确且互不一致（unknown/ambiguous/None 视为不明确）
     → conflict，说明跳过原因，不写标签。
  ⑤ 应用只补目标表缺失标签；重复执行因唯一约束与前置校验而幂等，不新增记录。
  ⑥ 应用在单事务内完成，任何写入失败整体回滚，两张表保持原样。

分类逻辑拆为纯函数 ``classify_sync_item``，不依赖数据库，可直接单测。
"""
from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.constants import error_codes as codes
from src.constants.enums import TagSource
from src.models.asset import Asset
from src.models.asset_column import AssetColumn
from src.models.semantic_tag import SemanticTag
from src.models.similarity_pair import SimilarityPair
from src.models.user import User
from src.schemas.common import asset_brief, tag_payload
from src.services import audit_service, similarity_engine
from src.services.tag_service import SENSITIVE_PREFIX
from src.utils.errors import AppError

# 预览项状态（前端 enums 有同名中文映射）
STATE_APPLY = "apply"
STATE_SKIPPED = "skipped"
STATE_CONFLICT = "conflict"

# 跳过 / 冲突原因码
REASON_TAG_EXISTS = "tag_exists"
REASON_SENSITIVE_EXISTS = "sensitive_exists"
REASON_TYPE_CONFLICT = "semantic_type_conflict"

# 推断后仍不算“明确语义”的类型：不参与冲突判定
_UNCLEAR_TYPES = {None, "", "unknown", "ambiguous"}


# --------------------------------------------------------------- 纯函数 ----
def is_conflicting_type(source_type: str | None, target_type: str | None) -> bool:
    """两列语义类型都明确且互不一致才判定冲突；任一不明确（未推断/unknown/ambiguous）不冲突。"""
    if source_type in _UNCLEAR_TYPES or target_type in _UNCLEAR_TYPES:
        return False
    return source_type != target_type


def classify_sync_item(
    *,
    tag_name: str,
    target_tag_names: Iterable[str],
    source_type: str | None,
    target_type: str | None,
) -> tuple[str, str]:
    """单条传播项的纯分类：返回 (state, reason)。

    state ∈ apply / skipped / conflict；reason 为空串表示可补标。
    判定顺序：同名标签 → 任意敏感标签 → 语义冲突 → 可补标，
    保证“已有判断的列保留原结论”优先于冲突提示。
    """
    existing = set(target_tag_names)
    if tag_name in existing:
        return STATE_SKIPPED, REASON_TAG_EXISTS
    if any(name.startswith(SENSITIVE_PREFIX) for name in existing):
        return STATE_SKIPPED, REASON_SENSITIVE_EXISTS
    if is_conflicting_type(source_type, target_type):
        return STATE_CONFLICT, REASON_TYPE_CONFLICT
    return STATE_APPLY, ""


# --------------------------------------------------------------- DB 装配 ----
def _load_pair(db: Session, pair_id: str) -> SimilarityPair:
    pair = db.get(SimilarityPair, pair_id)
    if pair is None:
        raise AppError(codes.NOT_FOUND, "相似表对不存在", f"pair_id={pair_id}")
    return pair


def _load_assets(db: Session, pair: SimilarityPair) -> tuple[Asset, Asset]:
    assets = db.scalars(
        select(Asset)
        .options(selectinload(Asset.columns))
        .where(Asset.id.in_([pair.left_asset_id, pair.right_asset_id]))
    ).all()
    by_id = {asset.id: asset for asset in assets}
    left, right = by_id.get(pair.left_asset_id), by_id.get(pair.right_asset_id)
    if left is None or right is None:
        raise AppError(codes.INTERNAL_ERROR, "相似表对关联的资产缺失", f"pair_id={pair.id}")
    return left, right


def _manual_sensitive_tags(db: Session, column_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[SemanticTag]]:
    """只取人工确认的敏感标签；inferred 与非 sensitive 标签不作为传播源。"""
    if not column_ids:
        return {}
    tags = db.scalars(
        select(SemanticTag)
        .where(SemanticTag.asset_column_id.in_(column_ids))
        .where(SemanticTag.source == TagSource.MANUAL.value)
        .where(SemanticTag.tag_name.like(f"{SENSITIVE_PREFIX}%"))
        .order_by(SemanticTag.asset_column_id, SemanticTag.tag_name)
    ).all()
    result: dict[uuid.UUID, list[SemanticTag]] = {}
    for tag in tags:
        result.setdefault(tag.asset_column_id, []).append(tag)
    return result


def _all_tags_by_column(db: Session, column_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[SemanticTag]]:
    if not column_ids:
        return {}
    tags = db.scalars(
        select(SemanticTag)
        .where(SemanticTag.asset_column_id.in_(column_ids))
        .order_by(SemanticTag.tag_name)
    ).all()
    result: dict[uuid.UUID, list[SemanticTag]] = {}
    for tag in tags:
        result.setdefault(tag.asset_column_id, []).append(tag)
    return result


def _matched_name_pairs(pair: SimilarityPair, left: Asset, right: Asset) -> list[dict[str, str]]:
    """优先用落库 suggestion.merged_columns；缺失时现场用相似度引擎重算（与 diff 口径一致）。"""
    merged = (pair.suggestion or {}).get("merged_columns")
    if merged:
        return [{"left": item["left"], "right": item["right"]} for item in merged]
    _, matched = similarity_engine.structure_similarity(
        [{"column_name": c.column_name, "data_type": c.data_type} for c in left.columns],
        [{"column_name": c.column_name, "data_type": c.data_type} for c in right.columns],
    )
    return matched


def _column_index(asset: Asset) -> dict[str, AssetColumn]:
    return {column.column_name: column for column in asset.columns}


def _column_brief(column: AssetColumn) -> dict[str, Any]:
    return {
        "id": str(column.id),
        "column_name": column.column_name,
        "data_type": column.data_type,
        "inferred_type": column.inferred_type,
        "inference_source": column.inference_source,
        "confidence": round(column.confidence or 0.0, 3),
    }


def _reason_text(reason: str, tag_name: str, source_col: AssetColumn, target_col: AssetColumn) -> str:
    if reason == REASON_TAG_EXISTS:
        return f"目标列已存在同名标签 {tag_name}，保留原结论"
    if reason == REASON_SENSITIVE_EXISTS:
        return "目标列已有人工/推断敏感标签，保留原结论不覆盖"
    if reason == REASON_TYPE_CONFLICT:
        return (
            f"语义类型冲突：源列 {source_col.inferred_type or 'unknown'} "
            f"≠ 目标列 {target_col.inferred_type or 'unknown'}，跳过传播"
        )
    return ""


def _build_preview(db: Session, pair: SimilarityPair) -> dict[str, Any]:
    left, right = _load_assets(db, pair)
    left_idx, right_idx = _column_index(left), _column_index(right)
    matched = _matched_name_pairs(pair, left, right)

    all_columns = list(left.columns) + list(right.columns)
    manual_tags = _manual_sensitive_tags(db, [c.id for c in all_columns])
    existing_tags = _all_tags_by_column(db, [c.id for c in all_columns])

    items: list[dict[str, Any]] = []

    def _emit(source_col: AssetColumn, target_col: AssetColumn, tag: SemanticTag,
              source_asset: Asset, target_asset: Asset) -> None:
        target_names = [t.tag_name for t in existing_tags.get(target_col.id, [])]
        state, reason = classify_sync_item(
            tag_name=tag.tag_name,
            target_tag_names=target_names,
            source_type=source_col.inferred_type,
            target_type=target_col.inferred_type,
        )
        items.append(
            {
                "state": state,
                "reason_code": reason,
                "reason": _reason_text(reason, tag.tag_name, source_col, target_col),
                "tag": tag_payload(tag),
                "direction": f"{source_asset.asset_key} → {target_asset.asset_key}",
                "source_asset_key": source_asset.asset_key,
                "target_asset_key": target_asset.asset_key,
                "source_column": _column_brief(source_col),
                "target_column": _column_brief(target_col),
            }
        )

    # 每个匹配列对只归并一次：左侧人工标签向右传播；右侧独有的人工标签（左侧没有同名标签）
    # 向左传播。两侧同名标签只产生一行 skip(tag_exists)，避免双向重复。
    for match in matched:
        left_col = left_idx.get(match["left"])
        right_col = right_idx.get(match["right"])
        if left_col is None or right_col is None:
            continue
        left_tag_names = {t.tag_name for t in existing_tags.get(left_col.id, [])}
        for tag in manual_tags.get(left_col.id, []):
            _emit(left_col, right_col, tag, left, right)
        for tag in manual_tags.get(right_col.id, []):
            if tag.tag_name in left_tag_names:
                continue
            _emit(right_col, left_col, tag, right, left)

    summary = {
        "apply": sum(1 for item in items if item["state"] == STATE_APPLY),
        "skipped": sum(1 for item in items if item["state"] == STATE_SKIPPED),
        "conflict": sum(1 for item in items if item["state"] == STATE_CONFLICT),
        "total": len(items),
    }
    return {
        "pair_id": str(pair.id),
        "left": asset_brief(left),
        "right": asset_brief(right),
        "matched_column_pairs": len(matched),
        "items": items,
        "summary": summary,
    }


def preview(db: Session, pair_id: str) -> dict[str, Any]:
    """同步预览：不落库，只返回补标 / 跳过 / 冲突明细与计数。"""
    pair = _load_pair(db, pair_id)
    return _build_preview(db, pair)


def apply_sync(db: Session, pair_id: str, actor: User) -> dict[str, Any]:
    """应用同步：服务端重算预览后，只给 apply 项的目标列补缺失标签。

    - 重算而非信任前端入参，保证规则口径唯一；
    - 全部插入在请求事务内（get_db 统一 commit/rollback），任一失败整体回滚；
    - 插入前再查一次同名标签，配合 uq_tag_column_name 唯一约束实现幂等，
      重复执行 created=0，不新增记录。
    """
    pair = _load_pair(db, pair_id)
    preview_payload = _build_preview(db, pair)
    apply_items = [item for item in preview_payload["items"] if item["state"] == STATE_APPLY]

    created = 0
    for item in apply_items:
        target_column_id = uuid.UUID(item["target_column"]["id"])
        tag_name = item["tag"]["tag_name"]
        existing = db.scalars(
            select(SemanticTag).where(
                SemanticTag.asset_column_id == target_column_id,
                SemanticTag.tag_name == tag_name,
            )
        ).first()
        if existing is not None:
            # 并发或重入下已被补上：幂等跳过，不计新增
            continue
        source_tag = item["tag"]
        db.add(
            SemanticTag(
                asset_column_id=target_column_id,
                tag_name=tag_name,
                category=source_tag["category"],
                source=TagSource.MANUAL.value,
                confidence=1.0,
                tagged_by=actor.email,
            )
        )
        created += 1
    db.flush()

    summary = preview_payload["summary"]
    audit_service.record(
        db,
        actor_email=actor.email,
        actor_role=actor.role,
        action="tag.sync_apply",
        entity_type="similarity_pair",
        entity_id=str(pair.id),
        detail=(
            f"敏感标签同步：新增 {created}，补标候选 {summary['apply']}，"
            f"跳过 {summary['skipped']}，冲突 {summary['conflict']}"
        ),
    )
    return {
        "pair_id": str(pair.id),
        "created": created,
        "summary": summary,
        "preview": preview_payload,
    }
