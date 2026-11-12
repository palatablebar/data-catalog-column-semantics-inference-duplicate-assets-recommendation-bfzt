"""列推断控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.user import User
from src.services import column_service


def summary(db: Session) -> dict:
    return column_service.infer_summary(db)


def list_columns(db: Session, **filters) -> dict:
    return column_service.list_columns(db, **filters)


def detail(db: Session, column_id: str) -> dict:
    return column_service.get_column(db, column_id)


def infer(db: Session, user: User) -> dict:
    return column_service.infer_all(db, user)


def correct(db: Session, column_id: str, inferred_type: str, note: str, user: User) -> dict:
    return column_service.correct_type(db, column_id, inferred_type, note, user)
