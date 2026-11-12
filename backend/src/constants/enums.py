"""共享枚举组 1：列语义类型 / 资产分层 / 任务与推荐状态。

前端等价定义见 frontend/src/constants/enums.ts（README 列出出现位置）。
"""
from __future__ import annotations

from enum import StrEnum


class ColumnSemanticType(StrEnum):
    """列语义类型：typing_engine 的 6 个真类型 + 2 个失败态。"""

    PHONE = "phone"
    ID_CARD = "id_card"
    EMAIL = "email"
    AMOUNT = "amount"
    DATETIME = "datetime"
    ENUM = "enum"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


TYPABLE_TYPES = (
    ColumnSemanticType.PHONE,
    ColumnSemanticType.ID_CARD,
    ColumnSemanticType.EMAIL,
    ColumnSemanticType.AMOUNT,
    ColumnSemanticType.DATETIME,
    ColumnSemanticType.ENUM,
)


class AssetLayer(StrEnum):
    """数仓分层：ods 原始 / dwd 明细 / dws 汇总 / ads 应用。"""

    ODS = "ods"
    DWD = "dwd"
    DWS = "dws"
    ADS = "ads"


class AssetSourceKind(StrEnum):
    """资产来源：有样例数据可采集 / 仅目录元数据。"""

    SAMPLE_TABLE = "sample_table"
    CATALOG_METADATA = "catalog_metadata"


class InferenceSource(StrEnum):
    """列类型来源：算法自动推断 / 人工纠正。"""

    AUTO = "auto"
    MANUAL = "manual"


class IngestJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PairStatus(StrEnum):
    RECOMMENDED = "recommended"
    DISMISSED = "dismissed"
    MERGED = "merged"


class TagSource(StrEnum):
    MANUAL = "manual"
    INFERRED = "inferred"


class TagCategory(StrEnum):
    PII = "pii"
    BUSINESS = "business"
    GOVERNANCE = "governance"
