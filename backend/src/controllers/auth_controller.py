"""认证控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.user import User
from src.schemas.common import user_payload
from src.services import auth_service


def login(db: Session, email: str, password: str) -> dict:
    user, token = auth_service.authenticate(db, email, password)
    return {"token": token, "user": user_payload(user)}


def me(user: User) -> dict:
    return {"user": user_payload(user)}
