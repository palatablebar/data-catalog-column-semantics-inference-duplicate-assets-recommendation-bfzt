"""样例表采样：从 DB schema sample 读 300 行表，产出列统计 + 抽样值。"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from worker_src.config.settings import settings


def to_text(value: Any) -> str | None:
    """把 DB 值统一转成可 JSON 存的文本（供 typing_engine 复用）。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return str(value)


def table_row_count(conn: Connection, schema: str, table: str) -> int:
    return int(conn.execute(text(f'SELECT count(*) FROM "{schema}"."{table}"')).scalar() or 0)


def column_names(conn: Connection, schema: str, table: str) -> list[str]:
    rows = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table ORDER BY ordinal_position"
        ),
        {"schema": schema, "table": table},
    ).all()
    return [row[0] for row in rows]


def profile_column(
    conn: Connection,
    schema: str,
    table: str,
    column: str,
    limit: int | None = None,
) -> dict[str, Any]:
    """单列采样：前 N 个原始值（含 NULL）+ 空值率/基数比/长度分布。"""
    limit = limit or settings.inference_sample_limit
    rows = conn.execute(
        text(f'SELECT "{column}" FROM "{schema}"."{table}" LIMIT :limit'),
        {"limit": limit},
    ).all()
    raw = [row[0] for row in rows]
    texts = [to_text(value) for value in raw]
    non_null = [value for value in texts if value is not None and value.strip() != ""]
    sample_count = len(texts)
    null_count = sample_count - len(non_null)
    lengths: dict[int, int] = {}
    for value in non_null:
        lengths[len(value)] = lengths.get(len(value), 0) + 1
    length_profile = [
        {"length": length, "count": count}
        for length, count in sorted(lengths.items(), key=lambda kv: (-kv[1], kv[0]))[:4]
    ]
    return {
        "sample_values": texts,
        "stats": {
            "sample_count": sample_count,
            "non_null_count": len(non_null),
            "null_rate": round(null_count / sample_count, 4) if sample_count else 1.0,
            "unique_count": len(set(non_null)),
            "unique_ratio": round(len(set(non_null)) / len(non_null), 4) if non_null else 0.0,
            "length_profile": length_profile,
            "profile_source": "worker_sample",
            "sample_limit": limit,
        },
    }
