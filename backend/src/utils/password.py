"""口令散列：stdlib PBKDF2-HMAC-SHA256（避免引入 bcrypt 原生依赖）。"""
from __future__ import annotations

import hashlib
import hmac
import secrets

_ITERATIONS = 120_000
_PREFIX = "pbkdf2_sha256"


def hash_password(raw: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS)
    return f"{_PREFIX}${_ITERATIONS}${salt}${digest.hex()}"


def verify_password(raw: str, hashed: str) -> bool:
    try:
        prefix, iterations, salt, expected = hashed.split("$", 3)
        if prefix != _PREFIX:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", raw.encode("utf-8"), salt.encode("utf-8"), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), expected)
    except Exception:  # noqa: BLE001
        return False
