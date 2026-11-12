"""列语义类型推断引擎（算法 A，纯 Python，不依赖 DB / 第三方库）。

口径（与 batch-plan gb-556 一致）：
  输入：列名 + 抽样值（≤200 个）
  ① 6 类正则命中率：手机号 / 身份证 18 位（含 GB11643 校验位）/ 邮箱 / 金额 / 日期时间 / 枚举
  ② 列名词典加分
  ③ 统计特征：基数比（唯一值/非空采样数）、空值率、长度分布
  ④ score = 0.55×正则命中率 + 0.20×词典 + 0.15×基数合理度 + 0.10×(1-空值率)
  输出：类型 + 置信度 + 证据列表（命中样本前 3）
  失败态：采样为空 → unknown/0；最高分 < 阈值 → unknown；前两名差 < 0.1 → ambiguous + 候选

本模块只做纯函数计算，落库由 column_service 负责，前端只展示落库结果。
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from src.constants.enums import ColumnSemanticType, TYPABLE_TYPES
from src.constants.limits import EVIDENCE_SAMPLE_LIMIT, SAMPLE_VALUE_LIMIT

# ------------------------------------------------------------------ 正则 ----
PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
ID_CARD_SHAPE_RE = re.compile(r"^\d{17}[0-9Xx]$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
# 金额：货币符号 / 千分位 / 两位小数至少命中一种，避免把整数计数误判成金额
AMOUNT_RE = re.compile(
    r"^(?:[¥￥$]\s?-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?"
    r"|-?(?:\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?"
    r"|-?\d+\.\d{1,2})$"
)
DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d",
    "%Y%m%d",
    "%Y年%m月%d日",
)

# GB11643-1999 公民身份号码校验位
ID_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
ID_CHECK_CHARS = "10X98765432"

# 列名词典：命中给 0.20 权重下的 1.0
DICT_PATTERNS: dict[str, re.Pattern[str]] = {
    ColumnSemanticType.PHONE.value: re.compile(r"(phone|mobile|tel|msisdn)"),
    ColumnSemanticType.ID_CARD.value: re.compile(r"(id_?card|idcard|cert|identity|id_no)"),
    ColumnSemanticType.EMAIL.value: re.compile(r"(e_?mail|mail)"),
    ColumnSemanticType.AMOUNT.value: re.compile(r"(amount|amt|price|money|fee|cost|revenue|total)"),
    ColumnSemanticType.DATETIME.value: re.compile(
        r"(date|time|_dt$|day$|month|year|timestamp|created_at|updated_at|birth)"
    ),
    ColumnSemanticType.ENUM.value: re.compile(r"(status|level|type|category|kind|class|flag|gender|grade)"),
}

NULL_TOKENS = {"", "null", "none", "nan", "n/a", "na", "-", "--", "\\n"}


# -------------------------------------------------------------- 校验位 ----
def id_card_checksum_ok(value: str) -> bool:
    """GB11643 校验位：前 17 位加权求和 mod 11 映射到校验字符。"""
    if not ID_CARD_SHAPE_RE.match(value):
        return False
    total = sum(int(ch) * weight for ch, weight in zip(value[:17], ID_WEIGHTS))
    return value[17].upper() == ID_CHECK_CHARS[total % 11]


def _is_null(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return text.lower() in NULL_TOKENS


def _parse_datetime(value: str) -> bool:
    for fmt in DATETIME_FORMATS:
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False


def _enum_vocabulary(values: list[str]) -> tuple[bool, list[str]]:
    """枚举判定：非空、去重后 2..12 个、基数比 ≤0.2、短文本、非纯数字。"""
    unique = sorted(set(values))
    if not 2 <= len(unique) <= 12:
        return False, unique
    if len(unique) / max(len(values), 1) > 0.2:
        return False, unique
    for item in unique:
        if len(item) > 24:
            return False, unique
        if re.fullmatch(r"-?\d+(\.\d+)?", item):
            return False, unique
    return True, unique


# ------------------------------------------------------------ 统计特征 ----
def _cardinality_fit(semantic_type: str, unique_ratio: float) -> float:
    """基数合理度：不同语义类型对基数比的期望区间不同，越界线性衰减。"""
    if semantic_type in (ColumnSemanticType.PHONE, ColumnSemanticType.EMAIL):
        return 1.0 if unique_ratio >= 0.5 else unique_ratio / 0.5
    if semantic_type == ColumnSemanticType.ID_CARD:
        return 1.0 if unique_ratio >= 0.8 else unique_ratio / 0.8
    if semantic_type in (ColumnSemanticType.AMOUNT, ColumnSemanticType.DATETIME):
        low, high = 0.02, 0.95
        if low <= unique_ratio <= high:
            return 1.0
        if unique_ratio < low:
            return unique_ratio / low
        return max(0.0, (1.0 - unique_ratio) / (1.0 - high))
    if semantic_type == ColumnSemanticType.ENUM:
        if unique_ratio <= 0.2:
            return 1.0
        return max(0.0, (0.45 - unique_ratio) / 0.25)
    return 0.5


def _length_profile(values: list[str]) -> dict[str, Any]:
    lengths = [len(item) for item in values]
    if not lengths:
        return {"min": 0, "max": 0, "mode": 0, "distinct": []}
    counts: dict[int, int] = {}
    for length in lengths:
        counts[length] = counts.get(length, 0) + 1
    mode = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))[0]
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:4]
    return {
        "min": min(lengths),
        "max": max(lengths),
        "mode": mode,
        "distinct": [{"length": length, "count": count} for length, count in top],
    }


# -------------------------------------------------------------- 主函数 ----
def infer_column(
    column_name: str,
    samples: list[Any] | None,
    *,
    data_type: str | None = None,
    sample_limit: int = SAMPLE_VALUE_LIMIT,
) -> dict[str, Any]:
    """对单列做语义类型推断，返回 {inferred_type, confidence, evidence, candidates, features}。"""
    raw = list(samples or [])[:sample_limit]
    values = [str(item).strip() for item in raw if not _is_null(item)]
    null_count = len(raw) - len(values)
    total = len(raw)
    null_rate = (null_count / total) if total else 1.0

    features: dict[str, Any] = {
        "column_name": column_name,
        "declared_type": data_type or "",
        "sample_count": total,
        "non_null_count": len(values),
        "null_rate": round(null_rate, 4),
        "unique_count": len(set(values)),
        "unique_ratio": round(len(set(values)) / max(len(values), 1), 4),
        "length": _length_profile(values),
        "regex_hit_rates": {},
        "dictionary_hits": {},
        "cardinality_fit": {},
        "scores": {},
    }

    if not values:
        return {
            "inferred_type": ColumnSemanticType.UNKNOWN.value,
            "confidence": 0.0,
            "evidence": ["采样为空（0 个非空值），无法推断，需人工确认"],
            "candidates": [],
            "features": features,
        }

    count = len(values)
    unique_ratio = len(set(values)) / count

    # ① 正则命中率 -------------------------------------------------------
    phone_hits = [item for item in values if PHONE_RE.match(item)]
    id_shape_hits = [item for item in values if ID_CARD_SHAPE_RE.match(item)]
    id_hits = [item for item in values if id_card_checksum_ok(item)]
    email_hits = [item for item in values if EMAIL_RE.match(item)]
    amount_hits = [item for item in values if AMOUNT_RE.match(item)]
    datetime_hits = [item for item in values if _parse_datetime(item)]
    enum_ok, enum_vocab = _enum_vocabulary(values)
    enum_hits = values if enum_ok else []

    hit_groups: dict[str, list[str]] = {
        ColumnSemanticType.PHONE.value: phone_hits,
        ColumnSemanticType.ID_CARD.value: id_hits,
        ColumnSemanticType.EMAIL.value: email_hits,
        ColumnSemanticType.AMOUNT.value: amount_hits,
        ColumnSemanticType.DATETIME.value: datetime_hits,
        ColumnSemanticType.ENUM.value: enum_hits,
    }
    rates = {key: len(hits) / count for key, hits in hit_groups.items()}
    features["regex_hit_rates"] = {key: round(value, 4) for key, value in rates.items()}
    features["id_card_shape_matches"] = len(id_shape_hits)
    features["enum_vocabulary"] = enum_vocab

    # ② 词典 -------------------------------------------------------------
    lowered = column_name.lower()
    dict_scores = {
        key: (1.0 if pattern.search(lowered) else 0.0) for key, pattern in DICT_PATTERNS.items()
    }
    features["dictionary_hits"] = dict_scores

    # ③ 基数合理度 -------------------------------------------------------
    fits = {key: _cardinality_fit(key, unique_ratio) for key in TYPABLE_TYPES}
    features["cardinality_fit"] = {key: round(value, 4) for key, value in fits.items()}

    # ④ 加权总分 ---------------------------------------------------------
    scores: dict[str, float] = {}
    for semantic_type in TYPABLE_TYPES:
        score = (
            0.55 * rates[semantic_type]
            + 0.20 * dict_scores[semantic_type]
            + 0.15 * fits[semantic_type]
            + 0.10 * (1.0 - null_rate)
        )
        scores[semantic_type] = round(score, 4)
    features["scores"] = scores

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    best_type, best_score = ranked[0]
    second_type, second_score = ranked[1] if len(ranked) > 1 else ("", 0.0)

    evidence = _build_evidence(
        column_name=column_name,
        values=values,
        best_type=best_type,
        random=(phone_hits, id_hits, email_hits, amount_hits, datetime_hits, enum_hits),
        scores=scores,
        null_rate=null_rate,
        unique_ratio=unique_ratio,
        id_shape_hits=id_shape_hits,
        enum_ok=enum_ok,
        dict_scores=dict_scores,
    )

    # 失败态 1：最高分不足阈值
    if best_score < 0.45:
        evidence.append(f"最高分 {best_score:.3f} < 0.45 阈值，判定 unknown")
        return {
            "inferred_type": ColumnSemanticType.UNKNOWN.value,
            "confidence": round(best_score, 3),
            "evidence": evidence,
            "candidates": [
                {"type": key, "score": round(value, 3)} for key, value in ranked[:3] if value > 0
            ],
            "features": features,
        }

    candidates = [
        {"type": key, "score": round(value, 3)} for key, value in ranked[:3] if value >= 0.2
    ]

    # 失败态 2：多类型高分接近（差 < 0.1）→ ambiguous
    if best_score - second_score < 0.1 and second_type:
        evidence.append(
            f"前两名分数接近（{best_type}={best_score:.3f} vs "
            f"{second_type}={second_score:.3f}，差 < 0.1），标记 ambiguous"
        )
        return {
            "inferred_type": ColumnSemanticType.AMBIGUOUS.value,
            "confidence": round(best_score, 3),
            "evidence": evidence,
            "candidates": candidates,
            "features": features,
        }

    return {
        "inferred_type": best_type,
        "confidence": round(best_score, 3),
        "evidence": evidence,
        "candidates": candidates,
        "features": features,
    }


def _build_evidence(
    *,
    column_name: str,
    values: list[str],
    best_type: str,
    random: tuple[list[str], list[str], list[str], list[str], list[str], list[str]],
    scores: dict[str, float],
    null_rate: float,
    unique_ratio: float,
    id_shape_hits: list[str],
    enum_ok: bool,
    dict_scores: dict[str, float],
) -> list[str]:
    phone_hits, id_hits, email_hits, amount_hits, datetime_hits, enum_hits = random
    count = len(values)
    hit_map: dict[str, list[str]] = {
        ColumnSemanticType.PHONE.value: phone_hits,
        ColumnSemanticType.ID_CARD.value: id_hits,
        ColumnSemanticType.EMAIL.value: email_hits,
        ColumnSemanticType.AMOUNT.value: amount_hits,
        ColumnSemanticType.DATETIME.value: datetime_hits,
        ColumnSemanticType.ENUM.value: enum_hits,
    }
    hits = hit_map.get(best_type, [])
    rate = len(hits) / count if count else 0.0
    evidence: list[str] = []

    label = {
        ColumnSemanticType.PHONE.value: "手机号正则 ^1[3-9]\\d{9}$",
        ColumnSemanticType.ID_CARD.value: "身份证 18 位 + GB11643 校验位",
        ColumnSemanticType.EMAIL.value: "邮箱正则",
        ColumnSemanticType.AMOUNT.value: "金额正则（货币符/千分位/两位小数）",
        ColumnSemanticType.DATETIME.value: "日期时间格式解析",
        ColumnSemanticType.ENUM.value: "枚举词表（≤12 个短值、基数比 ≤0.2）",
    }.get(best_type, best_type)

    evidence.append(f"主类型 {best_type}：{label} 命中率 {len(hits)}/{count}（{rate:.1%}）")
    if hits:
        sample_text = ", ".join(hits[:EVIDENCE_SAMPLE_LIMIT])
        evidence.append(f"命中样本前 {min(len(hits), EVIDENCE_SAMPLE_LIMIT)} 个：{sample_text}")

    if best_type == ColumnSemanticType.ID_CARD.value:
        passed = sum(1 for item in id_shape_hits if id_card_checksum_ok(item))
        evidence.append(
            f"GB11643 校验位：18 位形状命中 {len(id_shape_hits)} 个，校验位通过 {passed} 个"
        )
    if best_type == ColumnSemanticType.ENUM.value and enum_ok:
        evidence.append(f"枚举词表：{', '.join(sorted(set(values))[:12])}")
    if best_type == ColumnSemanticType.DATETIME.value and hits:
        parsed = datetime.strptime(
            hits[0], next(fmt for fmt in DATETIME_FORMATS if _try_format(hits[0], fmt))
        )
        evidence.append(f"解析示例：{hits[0]} → {parsed.date().isoformat()}")

    if dict_scores.get(best_type):
        evidence.append(f"列名词典命中：列名 `{column_name}` 匹配 {best_type} 关键词")
    evidence.append(f"基数比 {unique_ratio:.3f}（唯一值 {int(unique_ratio * count)}/{count}）")
    evidence.append(f"空值率 {null_rate:.1%}；加权总分 {scores[best_type]:.3f}")
    runner_up = max((key for key in scores if key != best_type), key=lambda key: scores[key])
    if scores[runner_up] > 0:
        evidence.append(f"次优候选 {runner_up} 分数 {scores[runner_up]:.3f}")
    return evidence


def _try_format(value: str, fmt: str) -> bool:
    try:
        datetime.strptime(value, fmt)
        return True
    except ValueError:
        return False


def infer_batch(columns: list[dict[str, Any]], sample_limit: int = SAMPLE_VALUE_LIMIT) -> dict[str, Any]:
    """批量推断并返回按类型聚合的统计，供 /columns/infer 响应使用。"""
    results: list[dict[str, Any]] = []
    by_type: dict[str, int] = {}
    for column in columns:
        result = infer_column(
            column.get("column_name", ""),
            column.get("sample_values"),
            data_type=column.get("data_type"),
            sample_limit=sample_limit,
        )
        result["column_id"] = column.get("id")
        results.append(result)
        by_type[result["inferred_type"]] = by_type.get(result["inferred_type"], 0) + 1
    return {"results": results, "by_type": by_type, "total": len(results)}
