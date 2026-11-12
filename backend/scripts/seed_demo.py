"""幂等演示数据入口：`docker compose exec -T backend python -m scripts.seed_demo`。

自然键：
- user: email
- asset: asset_key
- asset_column: (asset_id, column_name)
- semantic_tag: (asset_column_id, tag_name)
- similarity_pair: (left_asset_id, right_asset_id) —— 首次运行时用真实相似度引擎算出 6 对
- ingest_job: job_name
- 样例表：表存在且已有 300 行则跳过

重复执行不新增、不覆盖用户改动；结束时打印恰好一行 `SEED_SUMMARY k=v ...`。
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from src.config.database import engine, session_scope
from src.config.settings import settings
from src.constants.roles import Role
from src.models.asset import Asset
from src.models.asset_column import AssetColumn
from src.models.ingest_job import IngestJob
from src.models.semantic_tag import SemanticTag
from src.models.similarity_pair import SimilarityPair
from src.models.user import User
from src.services import catalog_fixtures, similarity_engine
from src.utils.logger import get_logger
from src.utils.password import hash_password
from sqlalchemy import func, select

logger = get_logger("catmap.seed")

DEMO_PASSWORD = "Demo@2026"
DEMO_USERS = [
    ("admin@catmap.demo", "平台管理员 · 何蔓", Role.ADMIN),
    ("analyst@catmap.demo", "数据分析 · 宋粼", Role.ANALYST),
    ("viewer@catmap.demo", "数据管家 · 顾原", Role.VIEWER),
]

CREATED = 0
SKIPPED = 0


def _log(kind: str, entity: str, key: str) -> None:
    global CREATED, SKIPPED
    if kind == "SEED_CREATED":
        CREATED += 1
    else:
        SKIPPED += 1
    print(f"{kind} entity={entity} key={key}", flush=True)


def _created(entity: str, key: str) -> None:
    _log("SEED_CREATED", entity, key)


def _skipped(entity: str, key: str) -> None:
    _log("SEED_SKIPPED", entity, key)


# ------------------------------------------------------------ 样例数据表 ----
def _ddl(schema: str, table: str, columns: list[dict]) -> str:
    column_sql = ", ".join(f'"{column["name"]}" {column["sql_type"]}' for column in columns)
    return f'CREATE TABLE IF NOT EXISTS "{schema}"."{table}" ({column_sql})'


def seed_sample_tables() -> None:
    """在 schema `sample` 里建 5 张真实样例表并灌 300 行（幂等）。"""
    catalog = catalog_fixtures.build_catalog()
    schema = settings.sample_schema
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        for table_name, payload in catalog["sample_tables"].items():
            conn.execute(text(_ddl(schema, table_name, payload["columns"])))
            existing = conn.execute(text(f'SELECT count(*) FROM "{schema}"."{table_name}"')).scalar()
            if existing and existing >= len(payload["rows"]):
                _skipped("SampleTable", table_name)
                continue
            conn.execute(text(f'TRUNCATE "{schema}"."{table_name}"'))
            column_names = [f'"{column["name"]}"' for column in payload["columns"]]
            placeholders = ", ".join(f":c{index}" for index in range(len(column_names)))
            insert_sql = text(
                f'INSERT INTO "{schema}"."{table_name}" ({", ".join(column_names)}) '
                f"VALUES ({placeholders})"
            )
            rows = [
                {f"c{index}": value for index, value in enumerate(row)}
                for row in payload["rows"]
            ]
            conn.execute(insert_sql, rows)
            _created("SampleTable", f"{table_name} rows={len(rows)}")


# ---------------------------------------------------------------- 用户 ----
def seed_users(db) -> dict[str, User]:
    users: dict[str, User] = {}
    for email, display_name, role in DEMO_USERS:
        existing = db.scalars(select(User).where(User.email == email)).first()
        if existing is None:
            existing = User(
                email=email,
                display_name=display_name,
                role=role.value,
                password_hash=hash_password(DEMO_PASSWORD),
            )
            db.add(existing)
            db.flush()
            _created("User", email)
        else:
            _skipped("User", email)
        users[role.value] = existing
    return users


# ---------------------------------------------------------------- 资产 ----
def seed_assets(db, catalog: dict) -> tuple[dict[str, Asset], int]:
    assets: dict[str, Asset] = {}
    created_columns = 0
    for item in catalog["assets"]:
        asset = db.scalars(select(Asset).where(Asset.asset_key == item["asset_key"])).first()
        if asset is None:
            asset = Asset(
                asset_key=item["asset_key"],
                schema_name=item["schema_name"],
                table_name=item["table_name"],
                layer=item["layer"],
                domain=item["domain"],
                owner_name=item["owner_name"],
                description=item["description"],
                row_count=item["row_count"],
                column_count=len(item["columns"]),
                source_kind=item["source_kind"],
                updated_at=item["updated_at"],
            )
            db.add(asset)
            db.flush()
            _created("Asset", item["asset_key"])
        else:
            _skipped("Asset", item["asset_key"])
        assets[item["asset_key"]] = asset
        existing_columns = {
            column.column_name
            for column in db.scalars(
                select(AssetColumn).where(AssetColumn.asset_id == asset.id)
            ).all()
        }
        for ordinal, column in enumerate(item["columns"], start=1):
            if column["column_name"] in existing_columns:
                continue
            db.add(
                AssetColumn(
                    asset_id=asset.id,
                    ordinal=ordinal,
                    column_name=column["column_name"],
                    data_type=column["data_type"],
                    nullable=column["nullable"],
                    comment=column["comment"],
                )
            )
            created_columns += 1
        if created_columns:
            asset.column_count = len(item["columns"])
    db.flush()
    return assets, created_columns


# ---------------------------------------------------------------- 标签 ----
def seed_tags(db, assets: dict[str, Asset]) -> None:
    for item in catalog_fixtures.TAG_SEED:
        asset = None
        for candidate in assets.values():
            if candidate.table_name == item["table_name"]:
                asset = candidate
                break
        if asset is None:
            _skipped("SemanticTag", f"{item['table_name']}.{item['column_name']}:{item['tag_name']}")
            continue
        column = db.scalars(
            select(AssetColumn).where(
                AssetColumn.asset_id == asset.id,
                AssetColumn.column_name == item["column_name"],
            )
        ).first()
        if column is None:
            _skipped("SemanticTag", f"{item['table_name']}.{item['column_name']}:{item['tag_name']}")
            continue
        existing = db.scalars(
            select(SemanticTag).where(
                SemanticTag.asset_column_id == column.id,
                SemanticTag.tag_name == item["tag_name"],
            )
        ).first()
        if existing is not None:
            _skipped("SemanticTag", f"{item['table_name']}.{item['column_name']}:{item['tag_name']}")
            continue
        db.add(
            SemanticTag(
                asset_column_id=column.id,
                tag_name=item["tag_name"],
                category=item["category"],
                source=item["source"],
                confidence=item["confidence"],
                tagged_by="system" if item["source"] == "inferred" else "admin@catmap.demo",
            )
        )
        db.flush()
        _created("SemanticTag", f"{item['table_name']}.{item['column_name']}:{item['tag_name']}")


# ------------------------------------------------------------ 相似表对 ----
def seed_similarity_pairs(db) -> None:
    """首次运行：真实跑 similarity_engine，落库 top N，并把最低分那对标为 dismissed。"""
    existing = db.scalars(select(SimilarityPair)).all()
    if existing:
        _skipped("SimilarityPair", f"already={len(existing)}")
        return

    assets = db.scalars(select(Asset).order_by(Asset.asset_key)).all()
    payload = []
    for asset in assets:
        columns = db.scalars(
            select(AssetColumn).where(AssetColumn.asset_id == asset.id).order_by(AssetColumn.ordinal)
        ).all()
        payload.append(
            {
                "asset_key": asset.asset_key,
                "table_name": asset.table_name,
                "layer": asset.layer,
                "row_count": asset.row_count,
                "columns": [
                    {"column_name": column.column_name, "data_type": column.data_type}
                    for column in columns
                ],
            }
        )
    ranking = similarity_engine.rank_table_pairs(
        payload, top_n=settings.similarity_top_n, min_score=settings.similarity_min_score
    )
    asset_by_key = {asset.asset_key: asset for asset in assets}
    created_pairs: list[SimilarityPair] = []
    for candidate in ranking["pairs"]:
        left = asset_by_key[candidate["left_key"]]
        right = asset_by_key[candidate["right_key"]]
        key_pair = tuple(sorted((left.id, right.id)))
        pair = SimilarityPair(
            left_asset_id=key_pair[0],
            right_asset_id=key_pair[1],
            score=candidate["score"],
            jaccard=candidate["jaccard"],
            structure_score=candidate["structure_score"],
            method=candidate["method"],
            status="recommended",
            suggestion=candidate["suggestion"],
        )
        db.add(pair)
        db.flush()
        created_pairs.append(pair)
        _created(
            "SimilarityPair",
            f"{candidate['left_table']}~{candidate['right_table']} score={candidate['score']}",
        )

    # 演一个"人工确认非重复"：最低分那一对置 dismissed，后续不再推荐
    if created_pairs:
        lowest = min(created_pairs, key=lambda pair: (pair.score, str(pair.id)))
        lowest.status = "dismissed"
        suggestion = dict(lowest.suggestion or {})
        suggestion["dismiss_note"] = "人工复核：两表口径不同（一张为明细、一张为汇总），非重复"
        suggestion["dismissed_by"] = "admin@catmap.demo"
        lowest.suggestion = suggestion
        _skipped("SimilarityPair", f"dismissed score={round(lowest.score, 3)}")


# ------------------------------------------------------------ 采集任务 ----
def seed_jobs(db) -> None:
    now = datetime.now(timezone.utc)
    for item in catalog_fixtures.JOB_SEED:
        existing = db.scalars(select(IngestJob).where(IngestJob.job_name == item["job_name"])).first()
        if existing is not None:
            _skipped("IngestJob", item["job_name"])
            continue
        started = None
        finished = None
        if item.get("started_hours_ago") is not None:
            started = now - timedelta(hours=item["started_hours_ago"])
        if item.get("started_minutes_ago") is not None:
            started = now - timedelta(minutes=item["started_minutes_ago"])
        if item.get("finished_hours_ago") is not None:
            finished = now - timedelta(hours=item["finished_hours_ago"])
        db.add(
            IngestJob(
                job_name=item["job_name"],
                connection_name=item["connection_name"],
                scope=item["scope"],
                status=item["status"],
                stats=item["stats"],
                error_code=item.get("error_code"),
                error_message=item.get("error_message"),
                triggered_by=item["triggered_by"],
                started_at=started,
                finished_at=finished,
            )
        )
        db.flush()
        _created("IngestJob", item["job_name"])


# ---------------------------------------------------------------- 入口 ----
def _counts(db) -> dict[str, int]:
    def count(model) -> int:
        return db.scalar(select(func.count()).select_from(model)) or 0

    return {
        "assets": count(Asset),
        "columns": count(AssetColumn),
        "tags": count(SemanticTag),
        "pairs": count(SimilarityPair),
        "jobs": count(IngestJob),
        "users": count(User),
    }


def seed_all() -> dict:
    global CREATED, SKIPPED
    CREATED = 0
    SKIPPED = 0

    catalog = catalog_fixtures.build_catalog()
    seed_sample_tables()
    with session_scope() as db:
        users = seed_users(db)
        assets, _ = seed_assets(db, catalog)
        seed_tags(db, assets)
        seed_similarity_pairs(db)
        seed_jobs(db)
        counts = _counts(db)

    summary = (
        f"SEED_SUMMARY assets={counts['assets']} columns={counts['columns']} tags={counts['tags']} "
        f"pairs={counts['pairs']} jobs={counts['jobs']} users={counts['users']}"
    )
    print(summary, flush=True)
    return {"summary": summary, "created": CREATED, "skipped": SKIPPED, **counts}


def main() -> int:
    try:
        result = seed_all()
    except Exception as exc:  # noqa: BLE001
        print(f"SEED_FAILED reason={exc}", file=sys.stderr, flush=True)
        return 1
    if result["assets"] == 0:
        print("SEED_FAILED reason=no assets", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
