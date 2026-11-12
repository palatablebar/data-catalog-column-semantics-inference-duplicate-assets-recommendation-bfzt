"""ORM 模型总入口；Alembic 通过 here 触发全部表注册。"""
from src.models.base import Base
from src.models.audit_log import AuditLog
from src.models.user import User
from src.models.asset import Asset
from src.models.asset_column import AssetColumn
from src.models.semantic_tag import SemanticTag
from src.models.similarity_pair import SimilarityPair
from src.models.ingest_job import IngestJob

__all__ = [
    "Base",
    "AuditLog",
    "User",
    "Asset",
    "AssetColumn",
    "SemanticTag",
    "SimilarityPair",
    "IngestJob",
]
