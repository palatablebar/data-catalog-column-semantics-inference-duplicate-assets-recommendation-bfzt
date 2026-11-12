"""相似表推荐服务（算法 B 的落库层）：recompute / 列表 / diff / 合并建议 / dismiss。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.enums import PairStatus, TagSource  # noqa: F401
from src.models.asset import Asset
from src.models.similarity_pair import SimilarityPair
from src.models.user import User
from src.schemas.common import asset_brief, iso
from src.services import audit_service, similarity_engine
from src.utils.errors import AppError


def _asset_with_columns(db: Session, asset_id: uuid.UUID) -> Asset | None:
    return db.scalars(
        select(Asset).options(selectinload(Asset.columns)).where(Asset.id == asset_id)
    ).first()


def _pair_key(left_id: uuid.UUID, right_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    return tuple(sorted((left_id, right_id)))  # type: ignore[return-value]


def recompute(db: Session, actor: User, *, top_n: int | None = None, min_score: float | None = None) -> dict:
    top_n = top_n or settings.similarity_top_n
    min_score = settings.similarity_min_score if min_score is None else min_score
    assets = db.scalars(select(Asset).options(selectinload(Asset.columns)).order_by(Asset.asset_key)).all()
    payload = [
        {
            "asset_key": asset.asset_key,
            "table_name": asset.table_name,
            "layer": asset.layer,
            "row_count": asset.row_count,
            "id": asset.id,
            "columns": [
                {"column_name": column.column_name, "data_type": column.data_type}
                for column in asset.columns
            ],
        }
        for asset in assets
    ]
    ranking = similarity_engine.rank_table_pairs(payload, top_n=top_n, min_score=min_score)

    existing = {
        _pair_key(pair.left_asset_id, pair.right_asset_id): pair
        for pair in db.scalars(select(SimilarityPair)).all()
    }
    asset_by_key = {asset.asset_key: asset for asset in assets}
    created = 0
    updated = 0
    now = datetime.now(timezone.utc)
    for candidate in ranking["pairs"]:
        left_asset = asset_by_key[candidate["left_key"]]
        right_asset = asset_by_key[candidate["right_key"]]
        key = _pair_key(left_asset.id, right_asset.id)
        pair = existing.get(key)
        if pair is None:
            pair = SimilarityPair(
                left_asset_id=key[0],
                right_asset_id=key[1],
                score=candidate["score"],
                jaccard=candidate["jaccard"],
                structure_score=candidate["structure_score"],
                method=candidate["method"],
                status=PairStatus.RECOMMENDED.value,
                suggestion=candidate["suggestion"],
            )
            db.add(pair)
            existing[key] = pair
            created += 1
        else:
            pair.score = candidate["score"]
            pair.jaccard = candidate["jaccard"]
            pair.structure_score = candidate["structure_score"]
            pair.method = candidate["method"]
            pair.suggestion = candidate["suggestion"]
            pair.computed_at = now
            updated += 1
    db.flush()

    audit_service.record(
        db,
        actor_email=actor.email,
        actor_role=actor.role,
        action="duplicate.recompute",
        entity_type="similarity_pair",
        detail=f"候选 {ranking['candidate_pairs']} 对，落库 top{top_n}，新增 {created} 更新 {updated}",
    )
    recommendations = _recommendations(db)
    return {
        "computed_pairs": ranking["computed_pairs"],
        "candidate_pairs": ranking["candidate_pairs"],
        "eligible_assets": ranking["eligible_assets"],
        "skipped_assets": ranking["skipped_assets"],
        "persisted_top_n": len(ranking["pairs"]),
        "created": created,
        "updated": updated,
        "recommendations": recommendations,
    }


def _pair_payload(db: Session, pair: SimilarityPair) -> dict:
    left = _asset_with_columns(db, pair.left_asset_id)
    right = _asset_with_columns(db, pair.right_asset_id)
    suggestion = pair.suggestion or {}
    return {
        "id": str(pair.id),
        "score": round(pair.score, 4),
        "jaccard": round(pair.jaccard, 4),
        "structure_score": round(pair.structure_score, 4),
        "method": pair.method,
        "status": pair.status,
        "verdict": suggestion.get("verdict", ""),
        "computed_at": iso(pair.computed_at),
        "left": {
            **_asset_brief(left),
            "owner_name": left.owner_name,
            "source_kind": left.source_kind,
        },
        "right": {
            **_asset_brief(right),
            "owner_name": right.owner_name,
            "source_kind": right.source_kind,
        },
        "suggestion": suggestion,
    }


def _asset_brief(asset: Asset) -> dict:
    return asset_brief(asset)


def _recommendations(db: Session) -> list[dict]:
    """按分数倒序返回推荐对；dismissed（人工确认非重复）不再推荐。"""
    pairs = db.scalars(
        select(SimilarityPair)
        .where(SimilarityPair.status != PairStatus.DISMISSED.value)
        .order_by(SimilarityPair.score.desc(), SimilarityPair.id)
    ).all()
    return [_pair_payload(db, pair) for pair in pairs]


def list_pairs(db: Session, *, limit: int = 5) -> dict:
    all_pairs = db.scalars(
        select(SimilarityPair).order_by(SimilarityPair.score.desc(), SimilarityPair.id)
    ).all()
    recommended_models = [
        pair for pair in all_pairs if pair.status != PairStatus.DISMISSED.value
    ]
    dismissed = [pair for pair in all_pairs if pair.status == PairStatus.DISMISSED.value]
    return {
        "items": [_pair_payload(db, pair) for pair in recommended_models[:limit]],
        "total": len(all_pairs),
        "recommended_total": len(recommended_models),
        "dismissed_total": len(dismissed),
        "true_duplicate_total": sum(1 for pair in recommended_models if pair.score >= 0.85),
        "top_n": limit,
    }


def get_pair(db: Session, pair_id: str) -> dict:
    pair = db.get(SimilarityPair, pair_id)
    if pair is None:
        raise AppError(codes.NOT_FOUND, "相似表对不存在", f"pair_id={pair_id}")
    left = _asset_with_columns(db, pair.left_asset_id)
    right = _asset_with_columns(db, pair.right_asset_id)
    payload = _pair_payload(db, pair)
    left_columns = [
        {
            "id": str(column.id),
            "column_name": column.column_name,
            "data_type": column.data_type,
            "inferred_type": column.inferred_type,
            "confidence": round(column.confidence or 0.0, 3),
        }
        for column in left.columns
    ]
    right_columns = [
        {
            "id": str(column.id),
            "column_name": column.column_name,
            "data_type": column.data_type,
            "inferred_type": column.inferred_type,
            "confidence": round(column.confidence or 0.0, 3),
        }
        for column in right.columns
    ]
    matched = (pair.suggestion or {}).get("merged_columns") or _matched_columns(left, right)
    payload.update(
        {
            "left_columns": left_columns,
            "right_columns": right_columns,
            "diff": _diff_rows(left_columns, right_columns, matched),
        }
    )
    return payload


def _matched_columns(left: Asset, right: Asset) -> list[dict]:
    _, matched = similarity_engine.structure_similarity(
        [{"column_name": column.column_name, "data_type": column.data_type} for column in left.columns],
        [{"column_name": column.column_name, "data_type": column.data_type} for column in right.columns],
    )
    return matched


def _diff_rows(left_columns: list[dict], right_columns: list[dict], matched: list[dict]) -> list[dict]:
    left_by_name = {item["column_name"]: item for item in left_columns}
    right_by_name = {item["column_name"]: item for item in right_columns}
    rows = []
    for match in matched:
        rows.append(
            {
                "state": "shared",
                "left_column": left_by_name.get(match["left"]),
                "right_column": right_by_name.get(match["right"]),
                "similarity": match.get("ratio", 1.0),
            }
        )
    matched_left = {match["left"] for match in matched}
    matched_right = {match["right"] for match in matched}
    for column in left_columns:
        if column["column_name"] not in matched_left:
            rows.append({"state": "left_only", "left_column": column, "right_column": None, "similarity": 0})
    for column in right_columns:
        if column["column_name"] not in matched_right:
            rows.append({"state": "right_only", "left_column": None, "right_column": column, "similarity": 0})
    return rows


def generate_merge_suggestion(db: Session, pair_id: str, actor: User) -> dict:
    pair = db.get(SimilarityPair, pair_id)
    if pair is None:
        raise AppError(codes.NOT_FOUND, "相似表对不存在", f"pair_id={pair_id}")
    left = _asset_with_columns(db, pair.left_asset_id)
    right = _asset_with_columns(db, pair.right_asset_id)
    merged = _matched_columns(left, right)
    payload = [
        {
            "asset_key": asset.asset_key,
            "table_name": asset.table_name,
            "row_count": asset.row_count,
            "columns": [
                {"column_name": column.column_name, "data_type": column.data_type}
                for column in asset.columns
            ],
        }
        for asset in (left, right)
    ]
    suggestion = similarity_engine.build_merge_suggestion(
        payload[0], payload[1], pair.score, pair.jaccard, pair.structure_score
    )
    suggestion["merged_columns"] = merged
    suggestion["generated_by"] = actor.email
    suggestion["generated_at"] = datetime.now(timezone.utc).isoformat()
    pair.suggestion = suggestion
    db.flush()
    audit_service.record(
        db,
        actor_email=actor.email,
        actor_role=actor.role,
        action="duplicate.merge_suggestion",
        entity_type="similarity_pair",
        entity_id=str(pair.id),
        detail=f"{suggestion['drop_asset_key']} → {suggestion['keep_asset_key']}（并集 {len(suggestion['union_columns'])} 列）",
    )
    return {"pair_id": str(pair.id), "suggestion": suggestion, "status": pair.status}


def dismiss(db: Session, pair_id: str, note: str, actor: User) -> dict:
    pair = db.get(SimilarityPair, pair_id)
    if pair is None:
        raise AppError(codes.NOT_FOUND, "相似表对不存在", f"pair_id={pair_id}")
    pair.status = PairStatus.DISMISSED.value
    suggestion = dict(pair.suggestion or {})
    suggestion["dismiss_note"] = note
    suggestion["dismissed_by"] = actor.email
    pair.suggestion = suggestion
    db.flush()
    audit_service.record(
        db,
        actor_email=actor.email,
        actor_role=actor.role,
        action="duplicate.dismiss",
        entity_type="similarity_pair",
        entity_id=str(pair.id),
        detail=note,
    )
    return {"pair_id": str(pair.id), "status": pair.status}
