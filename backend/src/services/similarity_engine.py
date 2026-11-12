"""相似表推荐引擎（算法 B，纯 Python，不依赖 DB / 第三方库）。

口径（与 batch-plan gb-556 一致）：
  ① 列签名：列名归一化（小写、去 ods_/dwd_ 前缀、_id 后缀同义合并）+ 类型桶
  ② 表签名 = 列签名集合
  ③ MinHash k=128 → 16 带 × 8 行 LSH → 候选对
  ④ 候选对精确 Jaccard + 列名结构相似（归一化编辑距离 >0.85 视为同列）
  ⑤ score = 0.7×jaccard + 0.3×结构相似 → top N 推荐 + 合并建议

失败态：列数 < 2 的表不参与；dismissed（人工确认非重复）由 service 层过滤不再推荐，
本模块只负责纯计算，不读不写数据库。
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from src.constants.limits import (
    LSH_BAND_COUNT,
    LSH_ROWS_PER_BAND,
    MINHASH_PERMUTATIONS,
    NAME_SIMILARITY_THRESHOLD,
)

LAYER_PREFIX_RE = re.compile(r"^(?:ods|dwd|dws|ads|dim|fact|tmp|dw|stg|src)_")
SUFFIX_RE = re.compile(r"(?:_?(?:id|no|code|num|number|key))$")
SYNONYM_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(mobile|msisdn|tel)"), "phone"),
    (re.compile(r"(e_?mail|mail)"), "email"),
    (re.compile(r"amt"), "amount"),
    (re.compile(r"(cert|id_?card|idcard)"), "idcard"),
    (re.compile(r"(shop|outlet|branch)"), "store"),
    (re.compile(r"cust"), "customer"),
    (re.compile(r"(qty|quantity)"), "quantity"),
)

TYPE_BUCKETS: dict[str, str] = {
    "text": "text",
    "varchar": "text",
    "char": "text",
    "string": "text",
    "uuid": "text",
    "int": "int",
    "int2": "int",
    "int4": "int",
    "int8": "int",
    "integer": "int",
    "bigint": "int",
    "smallint": "int",
    "serial": "int",
    "numeric": "numeric",
    "decimal": "numeric",
    "number": "numeric",
    "float": "numeric",
    "double": "numeric",
    "real": "numeric",
    "date": "temporal",
    "datetime": "temporal",
    "timestamp": "temporal",
    "timestamptz": "temporal",
    "time": "temporal",
    "bool": "bool",
    "boolean": "bool",
    "json": "json",
    "jsonb": "json",
}

_MERSENNE_PRIME = (1 << 61) - 1
MAX_HASH = (1 << 32) - 1


# ------------------------------------------------------------ 签名归一化 ----
def type_bucket(data_type: str | None) -> str:
    raw = (data_type or "text").strip().lower()
    match = re.match(r"^([a-z0-9_]+)", raw)
    base = match.group(1) if match else raw
    return TYPE_BUCKETS.get(base, "text")


def normalize_column_name(column_name: str) -> str:
    """小写 → 去分层前缀 → 同义词合并 → 去 _id/_no/_code 等后缀 → 去相邻重复 token。"""
    name = (column_name or "").strip().lower()
    name = LAYER_PREFIX_RE.sub("", name)
    name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    name = SUFFIX_RE.sub("", name)
    for pattern, replacement in SYNONYM_RULES:
        name = pattern.sub(replacement, name)
    name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    tokens = [token for token in name.split("_") if token]
    deduped: list[str] = []
    for token in tokens:
        if deduped and deduped[-1] == token:
            continue
        deduped.append(token)
    return "_".join(deduped) or name


def column_signature(column_name: str, data_type: str | None) -> str:
    return f"{normalize_column_name(column_name)}:{type_bucket(data_type)}"


def table_signature(columns: list[dict[str, Any]]) -> set[str]:
    return {
        column_signature(column.get("column_name", ""), column.get("data_type"))
        for column in columns
        if column.get("column_name")
    }


# --------------------------------------------------------------- MinHash ----
def _fnv1a(text: str, seed: int) -> int:
    """确定性 FNV-1a 64→32bit；避免 Python hash() 的进程级随机化。"""
    value = (2166136261 ^ seed) & MAX_HASH
    for byte in text.encode("utf-8"):
        value ^= byte
        value = (value * 16777619) & MAX_HASH
    return value


def minhash_signature(signature: set[str], permutations: int = MINHASH_PERMUTATIONS) -> list[int]:
    if not signature:
        return [MAX_HASH] * permutations
    vector: list[int] = []
    for index in range(permutations):
        seed = (index * 2654435761 + 97) & MAX_HASH
        vector.append(min(_fnv1a(item, seed) for item in signature))
    return vector


def lsh_candidates(
    minhashes: dict[str, list[int]],
    bands: int = LSH_BAND_COUNT,
    rows: int = LSH_ROWS_PER_BAND,
) -> set[tuple[str, str]]:
    """16 带 × 8 行分桶，同桶任一带命中的表对进入候选集。"""
    candidates: set[tuple[str, str]] = set()
    keys = sorted(minhashes)
    for band in range(bands):
        buckets: dict[tuple[int, ...], list[str]] = {}
        start = band * rows
        for key in keys:
            chunk = tuple(minhashes[key][start : start + rows])
            buckets.setdefault(chunk, []).append(key)
        for members in buckets.values():
            if len(members) < 2:
                continue
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    candidates.add((members[i], members[j]))
    return candidates


# ---------------------------------------------------------------- 相似度 ----
def exact_jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def structure_similarity(
    left_columns: list[dict[str, Any]],
    right_columns: list[dict[str, Any]],
    threshold: float = NAME_SIMILARITY_THRESHOLD,
) -> tuple[float, list[dict[str, Any]]]:
    """列名结构相似：归一化编辑距离 > 0.85 视为同列；返回 matched / min(lenA, lenB)。

    另返回 matched 明细（供并排 diff 建议使用）。
    """
    left = [
        {
            "name": column.get("column_name", ""),
            "normalized": normalize_column_name(column.get("column_name", "")),
            "bucket": type_bucket(column.get("data_type")),
        }
        for column in left_columns
    ]
    right = [
        {
            "name": column.get("column_name", ""),
            "normalized": normalize_column_name(column.get("column_name", "")),
            "bucket": type_bucket(column.get("data_type")),
        }
        for column in right_columns
    ]
    matched: list[dict[str, Any]] = []
    used_right: set[int] = set()
    for left_column in left:
        best_index = -1
        best_ratio = 0.0
        for index, right_column in enumerate(right):
            if index in used_right:
                continue
            if not _buckets_compatible(left_column["bucket"], right_column["bucket"]):
                continue
            ratio = SequenceMatcher(
                None, left_column["normalized"], right_column["normalized"]
            ).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_index = index
        if best_index >= 0 and best_ratio > threshold:
            used_right.add(best_index)
            matched.append(
                {
                    "left": left_column["name"],
                    "right": right[best_index]["name"],
                    "ratio": round(best_ratio, 3),
                }
            )
    denominator = min(len(left), len(right)) or 1
    return round(len(matched) / denominator, 4), matched


def _buckets_compatible(left: str, right: str) -> bool:
    if left == right:
        return True
    return {left, right} <= {"int", "numeric"} or {left, right} <= {"text", "json"}


def composite_score(jaccard: float, structure: float) -> float:
    """综合分：0.7×jaccard + 0.3×列名结构相似。"""
    return round(0.7 * jaccard + 0.3 * structure, 4)


def verdict_for(score: float) -> str:
    if score >= 0.95:
        return "identical_copy"
    if score >= 0.85:
        return "likely_duplicate"
    if score >= 0.65:
        return "review"
    return "weak"


# ----------------------------------------------------------- 主推荐流程 ----
def rank_table_pairs(
    assets: list[dict[str, Any]],
    *,
    top_n: int = 6,
    min_score: float = 0.45,
    permutations: int = MINHASH_PERMUTATIONS,
    bands: int = LSH_BAND_COUNT,
    rows: int = LSH_ROWS_PER_BAND,
) -> dict[str, Any]:
    """输入 42 张资产的列信息，输出 top N 相似表对（含 jaccard/结构分/合并建议素材）。

    assets: [{asset_key, table_name, layer, row_count, columns: [{column_name, data_type}]}]
    """
    eligible: dict[str, dict[str, Any]] = {}
    minhash_map: dict[str, list[int]] = {}
    signatures: dict[str, set[str]] = {}
    skipped: list[dict[str, Any]] = []

    for asset in assets:
        columns = asset.get("columns") or []
        if len(columns) < 2:
            skipped.append({"asset_key": asset.get("asset_key"), "reason": "columns_lt_2"})
            continue
        key = asset["asset_key"]
        signature = table_signature(columns)
        if not signature:
            skipped.append({"asset_key": key, "reason": "empty_signature"})
            continue
        eligible[key] = asset
        signatures[key] = signature
        minhash_map[key] = minhash_signature(signature, permutations=permutations)

    candidate_pairs = lsh_candidates(minhash_map, bands=bands, rows=rows)
    buckets: dict[str, dict[str, Any]] = {}
    for left_key, right_key in sorted(candidate_pairs):
        jaccard = exact_jaccard(signatures[left_key], signatures[right_key])
        if jaccard <= 0:
            continue
        structure, matched = structure_similarity(
            eligible[left_key]["columns"], eligible[right_key]["columns"]
        )
        score = composite_score(jaccard, structure)
        if score < min_score:
            continue
        left_asset = eligible[left_key]
        right_asset = eligible[right_key]
        bucket_key = _pair_key(left_key, right_key)
        buckets[bucket_key] = {
            "pair_key": bucket_key,
            "left_key": left_key,
            "right_key": right_key,
            "left_table": left_asset.get("table_name"),
            "right_table": right_asset.get("table_name"),
            "score": score,
            "jaccard": round(jaccard, 4),
            "structure_score": round(structure, 4),
            "method": "minhash-lsh",
            "verdict": verdict_for(score),
            "matched_columns": matched,
            "left_column_count": len(left_asset["columns"]),
            "right_column_count": len(right_asset["columns"]),
            "suggestion": build_merge_suggestion(left_asset, right_asset, score, jaccard, structure),
        }

    ranked = sorted(buckets.values(), key=lambda item: (-item["score"], item["pair_key"]))
    top = ranked[:top_n]
    return {
        "pairs": top,
        "recommended_total": len(ranked),
        "eligible_assets": len(eligible),
        "skipped_assets": skipped,
        "candidate_pairs": len(candidate_pairs),
        "computed_pairs": len(ranked),
    }


def _pair_key(left_key: str, right_key: str) -> str:
    first, second = sorted((left_key, right_key))
    return f"{first}||{second}"


# ------------------------------------------------------------ 合并建议 ----
def build_merge_suggestion(
    left_asset: dict[str, Any],
    right_asset: dict[str, Any],
    score: float,
    jaccard: float,
    structure: float,
) -> dict[str, Any]:
    """合并建议：下线哪张表、保留哪张、保留列的并集与缺口。"""
    left_cols = [column.get("column_name", "") for column in left_asset.get("columns") or []]
    right_cols = [column.get("column_name", "") for column in right_asset.get("columns") or []]
    left_set = set(left_cols)
    right_set = set(right_cols)
    union = sorted(left_set | right_set)
    only_left = sorted(left_set - right_set)
    only_right = sorted(right_set - left_set)

    # 下线策略：列更少/行数更少/表名更短的一方（稳定 tie-break 用 asset_key）
    left_weight = (len(left_cols), left_asset.get("row_count") or 0)
    right_weight = (len(right_cols), right_asset.get("row_count") or 0)
    if left_weight < right_weight:
        drop, keep = left_asset, right_asset
    elif right_weight < left_weight:
        drop, keep = right_asset, left_asset
    else:
        drop, keep = (
            (left_asset, right_asset)
            if left_asset["asset_key"] <= right_asset["asset_key"]
            else (right_asset, left_asset)
        )

    drop_only = only_left if drop is left_asset else only_right
    keep_only = only_right if drop is left_asset else only_left

    actions = [
        f"确认重复后下线 {drop.get('asset_key')}（{len(drop_only)} 个独有列迁入保留表）",
        f"保留 {keep.get('asset_key')} 作为唯一事实来源，补齐 {len(keep_only)} 个差异列",
        "更新下游依赖与调度，把查询切到保留表",
    ]
    return {
        "drop_asset_key": drop.get("asset_key"),
        "keep_asset_key": keep.get("asset_key"),
        "union_columns": union,
        "extra_in_drop": drop_only,
        "missing_in_drop": keep_only,
        "score": score,
        "jaccard": jaccard,
        "structure_score": structure,
        "verdict": verdict_for(score),
        "actions": actions,
    }
