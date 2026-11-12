"""输出格式化：置信度/比率统一保留 3 位小数，避免前端各写一套。"""
from __future__ import annotations


def round3(value: float | None) -> float:
    return round(float(value or 0.0), 3)


def percent(value: float | None) -> str:
    return f"{(float(value or 0.0) * 100):.1f}%"
