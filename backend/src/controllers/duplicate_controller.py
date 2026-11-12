"""相似表控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.user import User
from src.services import duplicate_service


def recompute(db: Session, user: User, top_n: int | None, min_score: float | None) -> dict:
    return duplicate_service.recompute(db, user, top_n=top_n, min_score=min_score)


def list_pairs(db: Session, limit: int) -> dict:
    return duplicate_service.list_pairs(db, limit=limit)


def detail(db: Session, pair_id: str) -> dict:
    return duplicate_service.get_pair(db, pair_id)


def merge_suggestion(db: Session, pair_id: str, user: User) -> dict:
    return duplicate_service.generate_merge_suggestion(db, pair_id, user)


def dismiss(db: Session, pair_id: str, note: str, user: User) -> dict:
    return duplicate_service.dismiss(db, pair_id, note, user)
