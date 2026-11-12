# catmap · 数据目录测绘台

> 合川零售（西南 180 家门店）数据治理组的「城市测绘地图册」：
> 把 42 张表 / 320 个列画成可检索的地图，用列语义推断找敏感列，用 MinHash+LSH 找重复表。

## 真实场景

- **模拟客户**：合川零售 · 数据治理组（5 人），面对 4000+ 张表没有数据目录。
- **现有工作流**：Excel 清单 + 口头问人找表；上游是数仓元数据采集，下游是分析师找数、平台管理员下线重复表、合规抽查。
- **三个痛点**：① 不知道该用哪张表，同一个「门店销售」有 7 张候选；② 重复表多（同义不同名、列几乎相同），存储白白涨；③ 手机号/身份证等敏感列没人标，合规抽查必挂。
- **角色权限**：

  | 角色 enum | 账号 | 权限 | 典型动作 |
  |---|---|---|---|
  | `admin` 平台管理员 | admin@catmap.demo | 全部写 + 采集 | 跑采集、重算相似表、生成合并建议、管标签 |
  | `analyst` 数据分析 | analyst@catmap.demo | 读 + 纠错标注 | 检索资产、纠正列类型推断 |
  | `viewer` 数据管家 | viewer@catmap.demo | 只读 + 打标签 + 导出 | 复核敏感标签、导出目录 CSV |

  口令统一：`Demo@2026`。

## 主要功能

1. **资产检索** `/assets`：左侧数仓分层/业务域树，右侧表详情 + 列卡片（`ColumnChip` 标注推断类型与敏感标签）。
2. **列语义推断校验** `/columns`：6 类正则 + 列名词典 + 基数/空值特征加权，展示证据（命中样本前 3）与置信度；支持人工纠正（记录 `manual` 来源）。
3. **相似表推荐** `/duplicates`：MinHash k=128 + 16 带×8 行 LSH 候选 → 精确 Jaccard + 列名结构相似；并排列级 diff + 合并建议（下线表 / 保留列并集）。
4. **标签与敏感列** `/tags`：manual/inferred 双来源标签；viewer 可批量补打 `sensitive:high`。
5. **采集任务** `/ingest`：Celery worker 读取 `sample` schema 的 5 张样例表（各 300 行），逐列统计落库；任务状态可轮询。
6. **导出目录 CSV**：`GET /api/assets/export.csv`，含资产 / 列 / 推断类型 / 标签。

## 两个核心算法（Python 真算，结果落库，前端只展示）

### A. 列语义类型推断 `backend/src/services/typing_engine.py`

- 输入：列名 + 抽样值（≤200 个，来自 worker 采集的 `asset_column.sample_values`）。
- 6 类正则命中率：手机号 `^1[3-9]\d{9}$`、身份证 18 位（**含 GB11643 校验位**）、邮箱、金额（货币符/千分位/两位小数）、日期时间（8 种格式）、枚举（≤12 个短值 + 基数比 ≤0.2）。
- 列名词典加分：`phone|mobile|tel`、`cert|id_card|idcard`、`email|mail`、`amt|amount|price`、`date|time|updated_at`、`status|level|type|category`。
- 统计特征：基数比（唯一值/非空采样）、空值率、长度分布。
- **score = 0.55×正则命中率 + 0.20×词典 + 0.15×基数合理度 + 0.10×(1-空值率)**。
- 输出：类型 + 置信度 + 证据列表（命中样本前 3、校验位通过数、词典命中、基数/空值率）。
- 失败态：采样为空 → `unknown`（置信度 0）；最高分 < 0.45 → `unknown`；前两名差 < 0.1 → `ambiguous` + 候选列表。
- 人工纠正的列不会被算法覆盖（`inference_source=manual`，置信度 1.0）。

### B. MinHash + LSH 相似表推荐 `backend/src/services/similarity_engine.py`

- 列签名：列名归一化（小写、去 `ods_/dwd_/dws_/ads_/dim_/fact_/tmp_` 前缀、`_id/_no/_code` 后缀同义合并、mobile/msisdn/tel→phone 等同义词合并）+ 类型桶。
- 表签名 = 列签名集合；MinHash k=128（确定性 FNV-1a，避免 Python hash 随机化）。
- 16 带 × 8 行 LSH → 候选对；候选对计算精确 Jaccard + 列名结构相似（归一化编辑距离 > 0.85 视为同列，取 matched / min(lenA,lenB)）。
- **score = 0.7×jaccard + 0.3×结构相似** → top N（默认 6）落库。
- 合并建议：下线列少/行少的一方，保留列并集、`extra_in_drop`、`missing_in_drop`、动作清单。
- 失败态：列 < 2 的表不参与；人工 `dismissed` 的对不再出现在推荐列表。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build
# 等 5 个容器 healthy（backend 首次启动会自动跑一次幂等 seed）
open http://localhost:18229
```

- 前端：http://localhost:18229
- 后端 OpenAPI：http://localhost:19229/api/docs
- PostgreSQL：`localhost:17729`（库 `catmap` / 用户 `catmap`）

手动 seed（幂等，会打印一行 `SEED_SUMMARY`）：

```bash
docker compose exec -T backend python -m scripts.seed_demo
# SEED_SUMMARY assets=42 columns=320 tags=8 pairs=6 jobs=3 users=3
```

## 本地开发

```bash
# 后端
cd backend && pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000

# worker
celery -A worker_src.config.celery_app worker -B -l info   # PYTHONPATH=/app:/app/backend

# 前端
cd frontend && npm install && npm run dev   # http://localhost:18229
```

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite（无 UI 框架，手写「城市测绘地图册」样式） |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 + PyJWT |
| 异步任务 | Celery 5.4 + Redis 7（worker 读样例表做列统计） |
| 数据库 | PostgreSQL 16（JSONB 存列统计/证据/合并建议） |
| 部署 | Docker Compose 5 服务：frontend(Nginx) / backend / worker / db / redis |
| 字体 | Playfair Display + Courier Prime（Google Fonts，离线回退 Songti SC / Courier New） |

## 目录

```
gb-556/
├── docker-compose.yml          # 5 服务 + 全部 healthcheck + 命名卷
├── .env.example
├── backend/
│   ├── Dockerfile  requirements.txt  entrypoint.sh  alembic.ini
│   ├── scripts/seed_demo.py    # 幂等 seed（打印 SEED_SUMMARY）
│   └── src/
│       ├── config/{settings,database,celery_app,app}.py
│       ├── constants/{enums,roles,error_codes,limits,tasks}.py
│       ├── middlewares/{auth,rbac,rate_limit,audit_logger,error_handler}.py
│       ├── models/{user,asset,asset_column,semantic_tag,similarity_pair,ingest_job,audit_log}.py
│       ├── schemas/  controllers/  routes/
│       ├── services/{typing_engine,similarity_engine,catalog_fixtures,...}.py
│       ├── utils/{jwt,password,errors,pagination,formatters,redis_client}.py
│       └── migrations/versions/0001_initial.py
├── worker/                     # Celery worker（采样 + 列统计 + 心跳）
└── frontend/src/{api,stores,types,components/common,components/catalog,hooks,pages,router,utils,constants,styles}
```

## 环境变量

| 变量 | 说明 | 默认 |
|---|---|---|
| `FRONTEND_PORT` / `BACKEND_PORT` / `DB_PORT` | 宿主端口 | 18229 / 19229 / 17729 |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | PostgreSQL 连接 | catmap / catmap / catmap_pwd_2026 |
| `JWT_SECRET` / `ACCESS_TOKEN_MINUTES` | JWT 签发 | 见 .env.example / 120 |
| `REDIS_URL` | Celery broker | redis://redis:6379/0 |
| `SAMPLE_SCHEMA` | 样例表 schema | sample |
| `INFERENCE_SAMPLE_LIMIT` | 推断采样上限 | 200 |
| `SIMILARITY_TOP_N` / `SIMILARITY_MIN_SCORE` | 相似表落库 top N / 阈值 | 6 / 0.45 |
| `RATE_LIMIT_PER_MINUTE` / `QUOTA_*` | 限流与每日配额 | 240 / 5000/2500/1200 |
| `SEED_DEMO` | 启动自动 seed | true |

## 共享枚举出现位置

- **组 1 `ColumnSemanticType`（phone/id_card/email/amount/datetime/enum/ambiguous/unknown）**
  - 后端：`backend/src/constants/enums.py`、`services/typing_engine.py`、`services/column_service.py`、`schemas/column.py`、`routes/columns.py`
  - 前端：`frontend/src/constants/enums.ts`、`types/models.ts`、`pages/ColumnsPage.vue`、`pages/TagsPage.vue`、`components/common/ColumnChip.vue`
- **组 2 `Role`（admin/analyst/viewer）**
  - 后端：`backend/src/constants/roles.py`、`constants/enums.py`、`middlewares/rbac.py`、`scripts/seed_demo.py`
  - 前端：`frontend/src/constants/enums.ts`、`types/models.ts`、`utils/permission.ts`、`components/common/RoleBadge.vue`、`pages/LoginPage.vue`
- 其它枚举：`AssetLayer`（ods/dwd/dws/ads）、`IngestJobStatus`（queued/running/completed/failed）、`PairStatus`（recommended/dismissed/merged）、`TagSource`（manual/inferred）、`TagCategory`（pii/business/governance）、`InferenceSource`（auto/manual）——后端 `constants/enums.py` 与前端 `constants/enums.ts` 各一份。

## Docker 说明

- 恰好 5 个容器，全部有 healthcheck；`db`/`redis` 用 `service_healthy` 作为 backend/worker 依赖，frontend 依赖 backend healthy。
- `backend` 启动时先 `alembic upgrade head` 再 `uvicorn`；`SEED_DEMO=true` 时启动后跑一次幂等 seed（失败只记日志不阻塞）。
- `worker` 使用与本项目同级的 `backend/`（共享模型与统计逻辑），任务名 `catmap.run_ingest`。
- 收尾：`docker compose down -v --remove-orphans`。

## License

内部演示项目，仅用于评审。
