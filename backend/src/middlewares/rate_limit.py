"""限流 + 配额中间件：每用户每分钟滑动窗口 + 每角色每日配额，超限 429。"""
from __future__ import annotations

import time
from datetime import date

from fastapi import Depends

from src.config.settings import settings
from src.constants import error_codes as codes
from src.constants.limits import RATE_LIMIT_WINDOW_SECONDS
from src.constants.roles import ROLE_LABELS, Role
from src.middlewares.auth import get_current_user
from src.models.user import User
from src.utils.errors import AppError
from src.utils.redis_client import get_redis


def _daily_quota(role: str) -> int:
    return {
        Role.ADMIN: settings.quota_admin,
        Role.ANALYST: settings.quota_analyst,
        Role.VIEWER: settings.quota_viewer,
    }.get(role, settings.quota_viewer)


def _check_minute(user: User) -> None:
    now = int(time.time())
    bucket = now // RATE_LIMIT_WINDOW_SECONDS
    key = f"ratelimit:{user.id}:{bucket}"
    try:
        client = get_redis()
        count = int(client.incr(key))
        if count == 1:
            client.expire(key, RATE_LIMIT_WINDOW_SECONDS * 2)
    except Exception:  # noqa: BLE001 - Redis 不可用时放行，不让限流打挂业务
        return
    if count > settings.rate_limit_per_minute:
        raise AppError(
            codes.RATE_LIMITED,
            "请求过于频繁，请稍后重试",
            f"user={user.email} count={count} limit={settings.rate_limit_per_minute}",
            extra={"retry_after": RATE_LIMIT_WINDOW_SECONDS},
        )


def _check_daily(user: User) -> None:
    key = f"quota:{user.id}:{date.today().isoformat()}"
    limit = _daily_quota(user.role)
    try:
        client = get_redis()
        count = int(client.incr(key))
        if count == 1:
            client.expire(key, 60 * 60 * 26)
    except Exception:  # noqa: BLE001
        return
    if count > limit:
        raise AppError(
            codes.QUOTA_EXCEEDED,
            f"{ROLE_LABELS.get(user.role, user.role)}今日写操作配额已用完（{limit} 次），请明日再试",
            f"user={user.email} count={count} quota={limit}",
        )


def rate_limit(bucket: str = "default"):  # noqa: ARG001 - bucket 只用于审计语义
    def dependency(user: User = Depends(get_current_user)) -> User:
        _check_minute(user)
        _check_daily(user)
        return user

    return Depends(dependency)
