"""敏感标签同步服务测试。

无 Postgres 环境：用 SQLite 内存库 + JSONB 编译兜底跑真实 ORM 与服务代码；
纯分类函数直接单测。运行方式（backend/ 目录下）：

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import unittest
import uuid

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as _PG_UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

# ---- SQLite 兼容：项目模型使用 PostgreSQL JSONB，测试时降级为 JSON ----
@compiles(JSONB, "sqlite")
def _jsonb_to_json(element, compiler, **kw):  # noqa: ANN001
    return "JSON"


def _patch_uuid_for_sqlite() -> None:
    """SQLite 下 PG UUID 缺少 bind processor：字符串形式的 UUID（如 JWT sub）先转 uuid.UUID。"""
    from sqlalchemy.dialects import sqlite as sqlite_dialect

    original = _PG_UUID.bind_processor

    def bind_processor(self, dialect):  # noqa: ANN001
        if isinstance(dialect, sqlite_dialect.dialect):
            def process(value):  # noqa: ANN001
                # SQLite DBAPI 只接受字符串：UUID 对象与 JWT 里的字符串 sub 统一归一
                if isinstance(value, uuid.UUID):
                    return str(value)
                if isinstance(value, str):
                    return str(uuid.UUID(value))
                return value
            return process
        return original(self, dialect)

    _PG_UUID.bind_processor = bind_processor


_patch_uuid_for_sqlite()


from src.constants.enums import TagSource  # noqa: E402
from src.constants.roles import ROLE_PERMISSIONS, Role  # noqa: E402
from src.models.asset import Asset  # noqa: E402
from src.models.asset_column import AssetColumn  # noqa: E402
from src.models.base import Base  # noqa: E402
from src.models.semantic_tag import SemanticTag  # noqa: E402
from src.models.similarity_pair import SimilarityPair  # noqa: E402
from src.models.user import User  # noqa: E402
from src.services import tag_sync_service as sync  # noqa: E402
from src.utils.errors import AppError  # noqa: E402


def make_engine():
    return create_engine("sqlite:///:memory:", future=True)


def make_session(engine) -> Session:
    Base.metadata.create_all(engine)
    return Session(engine)


def add_asset(session: Session, asset_key: str, columns: list[tuple[str, str]]) -> Asset:
    asset = Asset(
        asset_key=asset_key,
        schema_name="ods",
        table_name=asset_key,
        layer="ods",
        domain="会员",
        owner_name="tester",
        description="",
        row_count=100,
        column_count=len(columns),
        source_kind="sample_table",
    )
    session.add(asset)
    session.flush()
    for ordinal, (name, data_type) in enumerate(columns, start=1):
        session.add(
            AssetColumn(
                asset_id=asset.id, ordinal=ordinal, column_name=name,
                data_type=data_type, nullable=True, comment="",
            )
        )
    session.flush()
    return asset


def add_tag(session: Session, column: AssetColumn, tag_name: str, source: str,
            category: str = "pii") -> SemanticTag:
    tag = SemanticTag(
        asset_column_id=column.id, tag_name=tag_name, category=category,
        source=source, confidence=1.0 if source == TagSource.MANUAL.value else 0.9,
        tagged_by="admin@catmap.demo" if source == TagSource.MANUAL.value else "system",
    )
    session.add(tag)
    session.flush()
    return tag


def make_pair(session: Session, left: Asset, right: Asset, merged: list[dict]) -> SimilarityPair:
    pair = SimilarityPair(
        left_asset_id=left.id,
        right_asset_id=right.id,
        score=0.9,
        jaccard=0.8,
        structure_score=0.9,
        method="minhash-lsh",
        status="recommended",
        suggestion={"merged_columns": merged},
    )
    session.add(pair)
    session.flush()
    return pair


def actor(session: Session, role: Role = Role.VIEWER) -> User:
    user = User(
        email=f"{role}@catmap.demo", display_name=str(role),
        role=role, password_hash="x",
    )
    session.add(user)
    session.flush()
    return user


class ClassifyItemTests(unittest.TestCase):
    """纯函数：四类判定与优先级。"""

    def test_apply_when_target_has_no_sensitive_tag(self):
        state, reason = sync.classify_sync_item(
            tag_name="sensitive:high",
            target_tag_names=["business:metric"],
            source_type="phone",
            target_type="phone",
        )
        self.assertEqual((state, reason), (sync.STATE_APPLY, ""))

    def test_skip_when_same_tag_exists(self):
        state, reason = sync.classify_sync_item(
            tag_name="sensitive:high",
            target_tag_names=["sensitive:high"],
            source_type="phone",
            target_type="phone",
        )
        self.assertEqual(state, sync.STATE_SKIPPED)
        self.assertEqual(reason, sync.REASON_TAG_EXISTS)

    def test_skip_when_other_sensitive_tag_exists_keeps_original(self):
        state, reason = sync.classify_sync_item(
            tag_name="sensitive:high",
            target_tag_names=["sensitive:medium"],
            source_type="phone",
            target_type="phone",
        )
        self.assertEqual(state, sync.STATE_SKIPPED)
        self.assertEqual(reason, sync.REASON_SENSITIVE_EXISTS)

    def test_conflict_when_both_types_clear_and_differ(self):
        state, reason = sync.classify_sync_item(
            tag_name="sensitive:high",
            target_tag_names=[],
            source_type="phone",
            target_type="email",
        )
        self.assertEqual(state, sync.STATE_CONFLICT)
        self.assertEqual(reason, sync.REASON_TYPE_CONFLICT)

    def test_no_conflict_when_target_type_unclear(self):
        for unclear in (None, "", "unknown", "ambiguous"):
            with self.subTest(unclear=unclear):
                state, _ = sync.classify_sync_item(
                    tag_name="sensitive:high",
                    target_tag_names=[],
                    source_type="phone",
                    target_type=unclear,
                )
                self.assertEqual(state, sync.STATE_APPLY)

    def test_existing_tag_takes_precedence_over_conflict(self):
        # 已有同名标签时即使语义类型冲突，也按“保留原结论”跳过，不报冲突
        state, reason = sync.classify_sync_item(
            tag_name="sensitive:high",
            target_tag_names=["sensitive:high"],
            source_type="phone",
            target_type="email",
        )
        self.assertEqual(state, sync.STATE_SKIPPED)
        self.assertEqual(reason, sync.REASON_TAG_EXISTS)


class TagSyncServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine()
        self.session = make_session(self.engine)
        # A / B 两张会员域相似表：手机列同义不同名
        self.asset_a = add_asset(
            self.session, "ods.crm_a",
            [("mobile_no", "text"), ("email_addr", "text"), ("cust_name", "text")],
        )
        self.asset_b = add_asset(
            self.session, "ods.crm_b",
            [("mobile_phone", "text"), ("mail_box", "text"), ("cust_name", "text")],
        )
        self.cols_a = {c.column_name: c for c in self.asset_a.columns}
        self.cols_b = {c.column_name: c for c in self.asset_b.columns}
        self.pair = make_pair(
            self.session, self.asset_a, self.asset_b,
            merged=[
                {"left": "mobile_no", "right": "mobile_phone", "ratio": 0.9},
                {"left": "email_addr", "right": "mail_box", "ratio": 0.9},
                {"left": "cust_name", "right": "cust_name", "ratio": 1.0},
            ],
        )
        self.user = actor(self.session)
        # 夹具先落盘，后续用例里的 rollback 只会撤销当次写入，模拟真实请求事务边界
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def _tag_count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(SemanticTag)) or 0

    def test_preview_classifies_apply_skip_conflict_and_is_readonly(self):
        # 人工敏感标签（唯一可传播来源）
        add_tag(self.session, self.cols_a["mobile_no"], "sensitive:high", TagSource.MANUAL.value)
        # 目标已有同名标签 → skip(tag_exists)
        add_tag(self.session, self.cols_b["mobile_phone"], "sensitive:high", TagSource.MANUAL.value)
        # A 邮箱人工敏感；B 邮箱已有别的敏感结论 → skip(sensitive_exists)
        add_tag(self.session, self.cols_a["email_addr"], "sensitive:medium", TagSource.MANUAL.value)
        add_tag(self.session, self.cols_b["mail_box"], "sensitive:low", TagSource.INFERRED.value)
        # 反向：B 邮箱的 inferred 敏感标签不得被传播
        before = self._tag_count()

        preview = sync.preview(self.session, self.pair.id)

        self.assertEqual(self._tag_count(), before, "preview 不得写库")
        states = {(i["source_column"]["column_name"], i["target_column"]["column_name"],
                   i["tag"]["tag_name"]): i for i in preview["items"]}
        # 仅两个人工源标签产生传播项，inferred 不产生
        self.assertEqual(preview["summary"]["total"], 2)
        phone = states[("mobile_no", "mobile_phone", "sensitive:high")]
        mail = states[("email_addr", "mail_box", "sensitive:medium")]
        self.assertEqual(phone["state"], sync.STATE_SKIPPED)
        self.assertEqual(phone["reason_code"], sync.REASON_TAG_EXISTS)
        self.assertTrue(phone["reason"])
        self.assertEqual(mail["state"], sync.STATE_SKIPPED)
        self.assertEqual(mail["reason_code"], sync.REASON_SENSITIVE_EXISTS)
        self.assertEqual(preview["summary"], {"apply": 0, "skipped": 2, "conflict": 0, "total": 2})

    def test_apply_only_fills_missing_and_idempotent(self):
        add_tag(self.session, self.cols_a["mobile_no"], "sensitive:high", TagSource.MANUAL.value)
        add_tag(self.session, self.cols_a["email_addr"], "sensitive:medium", TagSource.MANUAL.value)
        # 构造一条冲突：把目标邮箱列改成明确但不同的语义
        self.cols_b["mail_box"].inferred_type = "email"
        self.cols_a["email_addr"].inferred_type = "phone"
        self.cols_a["mobile_no"].inferred_type = "phone"
        self.cols_b["mobile_phone"].inferred_type = "phone"

        preview = sync.preview(self.session, self.pair.id)
        self.assertEqual(preview["summary"], {"apply": 1, "skipped": 0, "conflict": 1, "total": 2})
        conflict = next(i for i in preview["items"] if i["state"] == sync.STATE_CONFLICT)
        self.assertEqual(conflict["reason_code"], sync.REASON_TYPE_CONFLICT)
        self.assertIn("phone", conflict["reason"])
        self.assertIn("email", conflict["reason"])

        before = self._tag_count()
        result = sync.apply_sync(self.session, self.pair.id, self.user)
        self.session.commit()

        self.assertEqual(result["created"], 1)
        self.assertEqual(self._tag_count(), before + 1)
        created = self.session.scalars(
            select(SemanticTag).where(
                SemanticTag.asset_column_id == self.cols_b["mobile_phone"].id,
                SemanticTag.tag_name == "sensitive:high",
            )
        ).one()
        self.assertEqual(created.source, TagSource.MANUAL.value)
        self.assertEqual(created.category, "pii")
        self.assertEqual(created.tagged_by, self.user.email)
        # 冲突列没有被写入任何标签
        self.assertEqual(
            self.session.scalar(
                select(func.count()).select_from(SemanticTag)
                .where(SemanticTag.asset_column_id == self.cols_b["mail_box"].id)
            ),
            0,
        )

        # 重复执行：不新增记录
        again = sync.apply_sync(self.session, self.pair.id, self.user)
        self.session.commit()
        self.assertEqual(again["created"], 0)
        self.assertEqual(again["summary"]["apply"], 0)
        self.assertEqual(self._tag_count(), before + 1)

    def test_inferred_tags_are_never_propagated(self):
        add_tag(self.session, self.cols_a["mobile_no"], "sensitive:high", TagSource.INFERRED.value)
        preview = sync.preview(self.session, self.pair.id)
        self.assertEqual(preview["summary"]["total"], 0)
        self.assertEqual(preview["items"], [])

    def test_apply_failure_rolls_back_both_tables(self):
        add_tag(self.session, self.cols_a["mobile_no"], "sensitive:high", TagSource.MANUAL.value)
        # 先把既有标签落盘，再挂失败钩子，保证钩子只拦截应用阶段的新标签
        self.session.commit()
        before = self._tag_count()

        def fail_on_flush(session_, flush_context, instances):  # noqa: ANN001
            if any(isinstance(obj, SemanticTag) for obj in session_.new):
                raise RuntimeError("simulated write failure")

        event.listen(Session, "before_flush", fail_on_flush)
        try:
            with self.assertRaises(RuntimeError):
                sync.apply_sync(self.session, self.pair.id, self.user)
        finally:
            event.remove(Session, "before_flush", fail_on_flush)
        self.session.rollback()

        # 两张表的标签数据保持原样：目标列没有新增，总量不变
        self.assertEqual(self._tag_count(), before)
        self.assertEqual(
            self.session.scalar(
                select(func.count()).select_from(SemanticTag)
                .where(SemanticTag.asset_column_id == self.cols_b["mobile_phone"].id)
            ),
            0,
        )
        # 原有人工标签仍在
        self.assertEqual(
            self.session.scalar(
                select(func.count()).select_from(SemanticTag)
                .where(SemanticTag.asset_column_id == self.cols_a["mobile_no"].id)
            ),
            1,
        )

    def test_pair_not_found_raises_app_error(self):
        with self.assertRaises(AppError):
            sync.preview(self.session, uuid.uuid4())

    def test_audit_record_written_on_apply(self):
        from src.models.audit_log import AuditLog

        add_tag(self.session, self.cols_a["mobile_no"], "sensitive:high", TagSource.MANUAL.value)
        sync.apply_sync(self.session, self.pair.id, self.user)
        self.session.commit()
        logs = self.session.scalars(
            select(AuditLog).where(AuditLog.action == "tag.sync_apply")
        ).all()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].actor_email, self.user.email)
        self.assertIn("新增 1", logs[0].detail)


class PermissionTests(unittest.TestCase):
    def test_tag_sync_allowed_for_all_three_roles(self):
        for role in (Role.ADMIN, Role.ANALYST, Role.VIEWER):
            with self.subTest(role=role):
                self.assertIn(role, ROLE_PERMISSIONS["tag:sync"])

    def test_routes_register_sync_endpoints(self):
        # redis 已安装，可直接装配路由；校验两个端点路径与方法
        from src.routes.duplicates import router

        paths = {(tuple(sorted(r.methods)), r.path) for r in router.routes}
        self.assertIn((("GET",), "/duplicates/{pair_id}/tag-sync/preview"), paths)
        self.assertIn((("POST",), "/duplicates/{pair_id}/tag-sync/apply"), paths)


if __name__ == "__main__":
    unittest.main()
