"""认证服务：校验口令并签发 JWT。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.models.user import User
from src.utils.errors import AppError
from src.utils.jwt import create_access_token
from src.utils.password import verify_password


def authenticate(db: Session, email: str, password: str) -> tuple[User, str]:
    user = db.scalars(select(User).where(User.email == email.lower().strip())).first()
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise AppError(codes.AUTH_INVALID, "邮箱或密码不正确", f"email={email}")
    token = create_access_token(str(user.id), user.role, user.email)
    return user, token
