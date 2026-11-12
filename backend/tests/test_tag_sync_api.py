"""端到端 HTTP 测试：FastAPI TestClient + SQLite 依赖覆盖，验证鉴权 / RBAC / 事务边界。"""
from __future__ import annotations

import unittest
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as _PG_UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from src.config.database import get_db
from src.config.settings import settings
from src.constants.enums import TagSource
from src.constants.roles import Role
from src.main import app
from src.models.base import Base
from src.models.semantic_tag import SemanticTag
from src.utils.jwt import create_access_token

from tests.test_tag_sync import add_asset, add_tag, actor, make_pair  # noqa: E402


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


class TagSyncApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 防止 lifespan 触发连 Postgres 的演示 seed
        settings.seed_demo = False
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        Base.metadata.create_all(cls.engine)

        def override_get_db():
            db = Session(cls.engine)
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        # raise_server_exceptions=False：交给应用的统一异常处理器返回 500，便于断言回滚行为
        cls.client = TestClient(app, raise_server_exceptions=False)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        cls.engine.dispose()

    def setUp(self):
        # 每用例一套干净数据
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            self.asset_a = add_asset(
                session, "ods.crm_a",
                [("mobile_no", "text"), ("email_addr", "text")],
            )
            self.asset_b = add_asset(
                session, "ods.crm_b",
                [("mobile_phone", "text"), ("mail_box", "text")],
            )
            cols_a = {c.column_name: c for c in self.asset_a.columns}
            cols_b = {c.column_name: c for c in self.asset_b.columns}
            self.pair = make_pair(
                session, self.asset_a, self.asset_b,
                merged=[
                    {"left": "mobile_no", "right": "mobile_phone", "ratio": 0.9},
                    {"left": "email_addr", "right": "mail_box", "ratio": 0.9},
                ],
            )
            # 一个可传播的人工敏感标签；邮箱也是人工标签，但两列语义类型冲突
            add_tag(session, cols_a["mobile_no"], "sensitive:high", TagSource.MANUAL.value)
            add_tag(session, cols_a["email_addr"], "sensitive:medium", TagSource.MANUAL.value)
            # 邮箱列构造语义冲突
            cols_a["email_addr"].inferred_type = "email"
            cols_b["mail_box"].inferred_type = "phone"
            self.target_column_id = str(cols_b["mobile_phone"].id)
            users = {role: actor(session, role) for role in Role}
            session.commit()
            self.pair_id = str(self.pair.id)
            self.tokens = {
                role: create_access_token(str(user.id), role, user.email)
                for role, user in users.items()
            }

    def _auth(self, role: Role) -> dict:
        return {"Authorization": f"Bearer {self.tokens[role]}"}

    def _tag_count(self) -> int:
        with Session(self.engine) as session:
            return session.scalar(select(func.count()).select_from(SemanticTag)) or 0

    def test_preview_requires_authentication(self):
        resp = self.client.get(f"/duplicates/{self.pair_id}/tag-sync/preview")
        self.assertEqual(resp.status_code, 401)

    def test_preview_shape_and_counts_for_viewer(self):
        resp = self.client.get(
            f"/duplicates/{self.pair_id}/tag-sync/preview",
            headers=self._auth(Role.VIEWER),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        # 人工手机标签可补标；人工邮箱标签因语义类型冲突被拦下
        self.assertEqual(body["summary"], {"apply": 1, "skipped": 0, "conflict": 1, "total": 2})
        apply_item = next(i for i in body["items"] if i["state"] == "apply")
        self.assertEqual(apply_item["tag"]["tag_name"], "sensitive:high")
        self.assertEqual(apply_item["tag"]["source"], "manual")
        self.assertEqual(apply_item["target_column"]["column_name"], "mobile_phone")
        conflict = next(i for i in body["items"] if i["state"] == "conflict")
        self.assertEqual(conflict["reason_code"], "semantic_type_conflict")
        self.assertIn("email", conflict["reason"])
        self.assertEqual(body["matched_column_pairs"], 2)

    def test_apply_then_repeat_is_idempotent(self):
        before = self._tag_count()
        resp = self.client.post(
            f"/duplicates/{self.pair_id}/tag-sync/apply",
            headers=self._auth(Role.VIEWER),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["created"], 1)
        self.assertEqual(self._tag_count(), before + 1)

        with Session(self.engine) as session:
            tag = session.scalars(
                select(SemanticTag).where(
                    SemanticTag.asset_column_id == uuid.UUID(self.target_column_id),
                    SemanticTag.tag_name == "sensitive:high",
                )
            ).one()
            self.assertEqual(tag.source, "manual")

        # 重复执行：预览里该项变为 skipped(tag_exists)，不再新增
        again = self.client.post(
            f"/duplicates/{self.pair_id}/tag-sync/apply",
            headers=self._auth(Role.VIEWER),
        )
        self.assertEqual(again.status_code, 200)
        self.assertEqual(again.json()["created"], 0)
        self.assertEqual(again.json()["summary"]["apply"], 0)
        self.assertEqual(again.json()["summary"]["skipped"], 1)
        self.assertEqual(again.json()["summary"]["conflict"], 1)
        self.assertEqual(self._tag_count(), before + 1)

    def test_all_roles_can_apply(self):
        for role in Role:
            with self.subTest(role=role):
                resp = self.client.post(
                    f"/duplicates/{self.pair_id}/tag-sync/apply",
                    headers=self._auth(role),
                )
                self.assertEqual(resp.status_code, 200, resp.text)

    def test_write_failure_returns_500_and_leaves_both_tables_untouched(self):
        before = self._tag_count()

        def fail_on_flush(session_, flush_context, instances):  # noqa: ANN001
            if any(isinstance(obj, SemanticTag) for obj in session_.new):
                raise RuntimeError("simulated write failure")

        event.listen(Session, "before_flush", fail_on_flush)
        try:
            resp = self.client.post(
                f"/duplicates/{self.pair_id}/tag-sync/apply",
                headers=self._auth(Role.ADMIN),
            )
        finally:
            event.remove(Session, "before_flush", fail_on_flush)

        self.assertEqual(resp.status_code, 500)
        self.assertEqual(self._tag_count(), before, "请求失败后整体回滚，两张表保持原样")

    def test_preview_unknown_pair_returns_404(self):
        resp = self.client.get(
            f"/duplicates/{uuid.uuid4()}/tag-sync/preview",
            headers=self._auth(Role.VIEWER),
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
