"""角色与权限矩阵（共享枚举组 2）。前端等价定义见 frontend/src/constants/enums.ts。"""
from __future__ import annotations

from enum import StrEnum

from src.constants import error_codes as codes
from src.utils.errors import AppError


class Role(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


ROLE_LABELS = {
    Role.ADMIN: "平台管理员",
    Role.ANALYST: "数据分析",
    Role.VIEWER: "数据管家",
}

# 权限动作 → 允许角色
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "asset:read": {Role.ADMIN, Role.ANALYST, Role.VIEWER},
    "asset:write": {Role.ADMIN},
    "column:read": {Role.ADMIN, Role.ANALYST, Role.VIEWER},
    "column:infer": {Role.ADMIN, Role.ANALYST},
    "column:correct": {Role.ADMIN, Role.ANALYST},
    "duplicate:read": {Role.ADMIN, Role.ANALYST, Role.VIEWER},
    "duplicate:recompute": {Role.ADMIN},
    "duplicate:merge": {Role.ADMIN},
    "duplicate:dismiss": {Role.ADMIN, Role.ANALYST},
    "tag:read": {Role.ADMIN, Role.ANALYST, Role.VIEWER},
    "tag:write": {Role.ADMIN, Role.ANALYST, Role.VIEWER},
    "ingest:read": {Role.ADMIN, Role.ANALYST, Role.VIEWER},
    "ingest:run": {Role.ADMIN},
    "export:run": {Role.ADMIN, Role.ANALYST, Role.VIEWER},
    "audit:read": {Role.ADMIN},
}

DAILY_QUOTA_BY_ROLE = {
    Role.ADMIN: "quota_admin",
    Role.ANALYST: "quota_analyst",
    Role.VIEWER: "quota_viewer",
}


def role_can(role: str, action: str) -> bool:
    allowed = ROLE_PERMISSIONS.get(action)
    if allowed is None:
        return False
    return role in allowed


def require_permission(role: str, action: str) -> None:
    """service 层兜底校验（路由层还有 require_permission 依赖）。"""
    if not role_can(role, action):
        raise AppError(
            codes.FORBIDDEN,
            f"当前角色（{ROLE_LABELS.get(role, role)}）无权执行该操作",
            f"role={role} action={action}",
        )
