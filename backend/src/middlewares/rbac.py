"""RBAC：require_permission(action) 依赖工厂；越权统一 403。"""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends

from src.constants import error_codes as codes
from src.constants.roles import ROLE_LABELS, role_can
from src.middlewares.auth import get_current_user
from src.models.user import User
from src.utils.errors import AppError


def require_permission(action: str) -> Callable[..., User]:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not role_can(user.role, action):
            raise AppError(
                codes.FORBIDDEN,
                f"当前角色（{ROLE_LABELS.get(user.role, user.role)}）无权执行该操作",
                f"role={user.role} action={action}",
            )
        return user

    return dependency
