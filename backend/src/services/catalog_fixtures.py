"""确定性目录样例数据（纯 Python，不依赖 DB）。

42 个资产 = 5 张真实样例表（各 300 行，可被 Celery 采集）+ 37 张仅目录元数据资产；
320 列 = 5×300 行表的 48 列 + 元数据表 272 列。

同一个随机种子在任意机器上生成同一批数据，保证 seed 幂等与算法结果可复现。
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from typing import Any

# ------------------------------------------------------------ 基础字典 ----
SURNAMES = ["张", "王", "李", "赵", "陈", "刘", "杨", "黄", "周", "吴", "徐", "孙", "马", "朱", "胡"]
PINYIN_SURNAMES = ["zhang", "wang", "li", "zhao", "chen", "liu", "yang", "huang", "zhou", "wu", "xu", "sun"]
GIVEN_NAMES = ["伟", "芳", "娜", "敏", "静", "磊", "洋", "勇", "艳", "杰", "涛", "明", "超", "霞", "平"]
CITIES = ["成都", "绵阳", "德阳", "宜宾"]
MEMBER_LEVELS = ["金卡", "银卡", "普卡"]
PAY_TYPES = ["微信支付", "支付宝", "现金", "银行卡"]
CONTACT_STATUS = ["启用", "停用"]
GENDERS = ["男", "女"]
STORE_NAMES = [f"合川{i}店" for i in range(1, 31)]
EMAIL_DOMAINS = ["qq.com", "163.com", "sina.com", "catmail.demo"]
PHONE_PREFIXES = ["138", "139", "150", "151", "158", "186", "187", "188", "133", "177"]
AREA_CODES = ["510101", "510104", "510108", "511301", "510701", "510601", "511501", "511701"]
ID_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
ID_CHECK_CHARS = "10X98765432"

ROW_COUNT = 300


def make_phone(rng: random.Random) -> str:
    return f"{rng.choice(PHONE_PREFIXES)}{rng.randint(10000000, 99999999)}"


def make_id_card(rng: random.Random, index: int) -> str:
    area = AREA_CODES[index % len(AREA_CODES)]
    birth = date(1965, 1, 1) + timedelta(days=rng.randint(0, 15000))
    sequence = f"{(index * 37 + rng.randint(0, 99)) % 1000:03d}"
    body = f"{area}{birth:%Y%m%d}{sequence}"
    total = sum(int(ch) * weight for ch, weight in zip(body, ID_WEIGHTS))
    return body + ID_CHECK_CHARS[total % 11]


def make_email(rng: random.Random, index: int, prefix: str = "") -> str:
    surname = rng.choice(PINYIN_SURNAMES)
    local = f"{prefix}{surname}{index % 97}{rng.randint(10, 99)}"
    return f"{local}@{rng.choice(EMAIL_DOMAINS)}"


def make_name(rng: random.Random) -> str:
    return f"{rng.choice(SURNAMES)}{rng.choice(GIVEN_NAMES)}{rng.choice(GIVEN_NAMES)}"


def make_amount(rng: random.Random, upper: float = 5000.0, *, thousands: bool = False) -> str:
    amount = round(rng.uniform(5.0, upper), 2)
    if thousands:
        return f"¥{amount:,.2f}"
    return f"{amount:.2f}"


# ----------------------------------------------------------- 真实样例表 ----
REAL_TABLES: list[dict[str, Any]] = [
    {
        "table_name": "ods_crm_customer",
        "layer": "ods",
        "domain": "会员",
        "owner": "陈亭",
        "description": "CRM 客户主档：手机号 / 邮箱 / 身份证为合规敏感列",
        "columns": [
            ("customer_id", "text"),
            ("cust_name", "text"),
            ("mobile_no", "text"),
            ("email_addr", "text"),
            ("id_card_no", "text"),
            ("city", "text"),
            ("register_date", "date"),
            ("member_level", "text"),
            ("total_amount", "numeric(12,2)"),
            ("updated_at", "timestamp"),
        ],
    },
    {
        "table_name": "ods_member_contact",
        "layer": "ods",
        "domain": "会员",
        "owner": "陈亭",
        "description": "会员联系方式：紧急联系人电话与身份证号",
        "columns": [
            ("member_id", "text"),
            ("member_name", "text"),
            ("mobile_phone", "text"),
            ("backup_phone", "text"),
            ("emergency_phone", "text"),
            ("mail_box", "text"),
            ("cert_no", "text"),
            ("contact_city", "text"),
            ("contact_status", "text"),
            ("created_at", "timestamp"),
        ],
    },
    {
        "table_name": "dwd_sales_store_day",
        "layer": "dwd",
        "domain": "交易",
        "owner": "王珂",
        "description": "门店销售明细日表（交易域核心事实表，含装载时间列）",
        "columns": [
            ("store_no", "text"),
            ("store_name", "text"),
            ("biz_date", "date"),
            ("sku_code", "text"),
            ("qty", "integer"),
            ("sales_amount", "numeric(12,2)"),
            ("discount_amount", "numeric(12,2)"),
            ("pay_type", "text"),
            ("updated_at", "timestamp"),
            ("etl_loaded_at", "timestamp"),
        ],
    },
    {
        "table_name": "dwd_store_sales_daily",
        "layer": "dwd",
        "domain": "交易",
        "owner": "王珂",
        "description": "门店销售明细日表（历史遗留重复表，缺装载时间列，待下线）",
        "columns": [
            ("store_no", "text"),
            ("store_name", "text"),
            ("biz_date", "date"),
            ("sku_code", "text"),
            ("qty", "integer"),
            ("sales_amount", "numeric(12,2)"),
            ("discount_amount", "numeric(12,2)"),
            ("pay_type", "text"),
            ("updated_at", "timestamp"),
        ],
    },
    {
        "table_name": "dws_member_profile",
        "layer": "dws",
        "domain": "会员",
        "owner": "李牧",
        "description": "会员画像宽表：手机 / 备用机 / 邮箱",
        "columns": [
            ("member_id", "text"),
            ("mobile", "text"),
            ("phone_2", "text"),
            ("email", "text"),
            ("gender", "text"),
            ("birth_date", "date"),
            ("city", "text"),
            ("total_amount", "numeric(12,2)"),
            ("updated_at", "timestamp"),
        ],
    },
]


def _build_crm_customer_rows(rng: random.Random) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for index in range(ROW_COUNT):
        phone = make_phone(rng)
        if index in (17, 188):
            phone = "1380000"  # 脏数据：位数不足
        mobile = None if index % 50 == 3 else phone
        email = None if index in (5, 23, 61, 99, 140, 210) else make_email(rng, index, "cust")
        id_card = None if index in (44, 177) else make_id_card(rng, index)
        register = date(2025, 1, 1) + timedelta(days=index % 420)
        rows.append(
            [
                f"C{100000 + index}",
                make_name(rng),
                mobile,
                email,
                id_card,
                CITIES[index % len(CITIES)],
                register,
                MEMBER_LEVELS[index % len(MEMBER_LEVELS)],
                make_amount(rng, 12000.0, thousands=(index % 7 == 0)),
                datetime(2026, 11, 9, 8 + index % 10, index % 60, 0),
            ]
        )
    return rows


def _build_member_contact_rows(rng: random.Random) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for index in range(ROW_COUNT):
        rows.append(
            [
                f"M{index + 1:04d}",
                make_name(rng),
                make_phone(rng),
                None if index % 10 == 4 else make_phone(rng),
                None if index % 5 == 0 else make_phone(rng),
                make_email(rng, index, "mb"),
                make_id_card(rng, index + 2),
                CITIES[(index + 1) % len(CITIES)],
                CONTACT_STATUS[index % 2],
                datetime(2026, 10, 1, 9, (index * 2) % 60, 0) + timedelta(days=index % 60),
            ]
        )
    return rows


def _build_sales_rows(rng: random.Random, *, with_etl: bool) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for index in range(ROW_COUNT):
        row: list[Any] = [
            f"S{(index % 30) + 1:03d}",
            STORE_NAMES[index % len(STORE_NAMES)],
            date(2026, 1, 1) + timedelta(days=index),
            f"SKU{index + 1:04d}",
            (index % 20) + 1,
            make_amount(rng, 3000.0),
            make_amount(rng, 300.0),
            PAY_TYPES[index % len(PAY_TYPES)],
            datetime(2026, 11, 9, 2, 0, 0),
        ]
        if with_etl:
            row.append(datetime(2026, 11, 9, 2, 5, 0))
        rows.append(row)
    return rows


def _build_member_profile_rows(rng: random.Random) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for index in range(ROW_COUNT):
        birth = date(1960, 1, 1) + timedelta(days=rng.randint(0, 16000))
        rows.append(
            [
                f"M{index + 1:04d}",
                make_phone(rng),
                None if index % 10 < 3 else make_phone(rng),
                make_email(rng, index, "prof"),
                GENDERS[index % 2],
                birth,
                CITIES[(index + 2) % len(CITIES)],
                make_amount(rng, 26000.0, thousands=(index % 5 == 0)),
                datetime(2026, 11, 8, 6, index % 60, 0),
            ]
        )
    return rows


def build_sample_tables() -> dict[str, dict[str, Any]]:
    """5 张真实样例表：DDL 列 + 300 行数据，写入 DB schema `sample`。"""
    rng = random.Random(55601)
    tables = {
        "ods_crm_customer": _build_crm_customer_rows(rng),
        "ods_member_contact": _build_member_contact_rows(rng),
        "dwd_sales_store_day": _build_sales_rows(rng, with_etl=True),
        "dwd_store_sales_daily": _build_sales_rows(rng, with_etl=False),
        "dws_member_profile": _build_member_profile_rows(rng),
    }
    payload: dict[str, dict[str, Any]] = {}
    for table in REAL_TABLES:
        name = table["table_name"]
        payload[name] = {
            # ODS 原始表把金额列存成文本（含 ¥/千分位），列目录里声明为 numeric 是业务口径
            "columns": [
                {"name": col, "sql_type": "text" if sql_type.startswith("numeric") else sql_type}
                for col, sql_type in table["columns"]
            ],
            "rows": tables[name],
        }
    return payload


# --------------------------------------------------------- 仅元数据资产 ----
# 3 张刻意做成"重复表"的元数据资产（用于相似度算法验收）
DESIGNED_DUPLICATES: list[dict[str, Any]] = [
    {
        "table_name": "ads_store_sales_day",
        "layer": "ads",
        "domain": "交易",
        "owner": "王珂",
        "description": "应用层门店销售日汇总（直接从 dwd_sales_store_day 复制）",
        "copy_columns_from": "dwd_sales_store_day",
        "extra_columns": [],
    },
    {
        "table_name": "dw_member_contact_old",
        "layer": "dwd",
        "domain": "会员",
        "owner": "陈亭",
        "description": "旧版会员联系方式（手机列改名 contact_phone）",
        "copy_columns_from": "ods_member_contact",
        "rename": {"mobile_phone": "contact_phone"},
        "extra_columns": [],
    },
    {
        "table_name": "tmp_sales_store_day_bak",
        "layer": "ods",
        "domain": "交易",
        "owner": "赵铭",
        "description": "销售日表迁移备份（多一个批量号列）",
        "copy_columns_from": "dwd_sales_store_day",
        "extra_columns": [("batch_no", "text")],
    },
]

# 34 张普通元数据资产：(表名, 分层, 域, 负责人, 描述)
METADATA_THEMES: list[tuple[str, str, str, str, str]] = [
    ("ads_trade_order_daily", "ads", "交易", "王珂", "交易订单日汇总"),
    ("dwd_order_payment_detail", "dwd", "交易", "王珂", "支付流水明细"),
    ("dws_channel_settlement_monthly", "dws", "交易", "周颖", "渠道结算月表"),
    ("ads_refund_analysis_weekly", "ads", "交易", "王珂", "退款分析周报"),
    ("dwd_coupon_usage_detail", "dwd", "交易", "赵铭", "优惠券核销明细"),
    ("dws_payment_channel_summary", "dws", "交易", "周颖", "支付渠道汇总"),
    ("ads_member_growth_monthly", "ads", "会员", "陈亭", "会员增长月报"),
    ("dws_member_loyalty_score", "dws", "会员", "陈亭", "会员忠诚度评分"),
    ("dwd_member_consent_log", "dwd", "会员", "李牧", "会员授权日志"),
    ("ads_member_segment_profile", "ads", "会员", "陈亭", "会员分群画像"),
    ("dws_member_points_balance", "dws", "会员", "陈亭", "会员积分余额"),
    ("dws_store_operation_daily", "dws", "门店", "王珂", "门店运营日报"),
    ("ads_store_traffic_hourly", "ads", "门店", "王珂", "门店客流小时表"),
    ("dwd_store_layout_snapshot", "dwd", "门店", "李牧", "门店布局快照"),
    ("dws_region_target_progress", "dws", "门店", "周颖", "区域目标进度"),
    ("ads_store_staffing_plan", "ads", "门店", "赵铭", "门店排班计划"),
    ("dws_product_sku_master", "dws", "商品", "李牧", "SKU 主数据"),
    ("dwd_product_brand_mapping", "dwd", "商品", "李牧", "品牌映射"),
    ("ads_product_category_sales", "ads", "商品", "赵铭", "品类销售"),
    ("dws_supplier_scorecard", "dws", "商品", "李牧", "供应商评分卡"),
    ("dwd_inventory_snapshot_daily", "dwd", "库存", "赵铭", "库存日快照"),
    ("dws_warehouse_capacity", "dws", "库存", "赵铭", "仓容利用率"),
    ("ads_stock_reorder_alert", "ads", "库存", "周颖", "补货预警"),
    ("dwd_inventory_transfer_log", "dwd", "库存", "赵铭", "库存调拨日志"),
    ("ads_campaign_roi_daily", "ads", "营销", "周颖", "活动 ROI 日报"),
    ("dws_audience_exposure_hourly", "dws", "营销", "周颖", "人群曝光小时表"),
    ("dwd_coupon_creative_detail", "dwd", "营销", "王珂", "券创意明细"),
    ("ads_budget_placement_monthly", "ads", "营销", "王珂", "预算投放月报"),
    ("dwd_delivery_parcel_trace", "dwd", "履约", "李牧", "包裹轨迹"),
    ("dws_carrier_eta_summary", "dws", "履约", "李牧", "承运商时效汇总"),
    ("ads_return_exchange_daily", "ads", "履约", "赵铭", "退换货日报"),
    ("dwd_finance_ledger_entry", "dwd", "财务", "周颖", "财务凭证分录"),
    ("dws_cost_margin_by_store", "dws", "财务", "周颖", "门店成本毛利"),
    ("ads_tax_invoice_summary", "ads", "财务", "王珂", "发票汇总"),
]

METADATA_BASES: dict[str, list[str]] = {
    "交易": ["order", "promo", "coupon", "invoice", "refund", "settle", "channel", "campaign", "payment", "voucher"],
    "会员": ["member", "vip", "loyalty", "points", "growth", "consent", "preference", "segment", "birthday", "referral"],
    "门店": ["store", "outlet", "region", "district", "opening", "closing", "layout", "staffing", "audit", "target"],
    "商品": ["sku", "spu", "brand", "category", "supplier", "barcode", "season", "color", "size", "pack"],
    "库存": ["stock", "warehouse", "bin", "inbound", "outbound", "reorder", "safety", "cycle", "transfer", "shrink"],
    "营销": ["activity", "banner", "exposure", "click", "conversion", "roi", "budget", "audience", "creative", "placement"],
    "履约": ["delivery", "carrier", "parcel", "route", "dispatch", "eta", "return", "exchange", "slot", "zone"],
    "财务": ["ledger", "journal", "account", "tax", "invoice", "budget", "cost", "profit", "margin", "settlement"],
}
METADATA_SUFFIXES: list[tuple[str, str]] = [
    ("_code", "text"),
    ("_name", "text"),
    ("_no", "text"),
    ("_time", "timestamp"),
    ("_date", "date"),
    ("_amount", "numeric(14,2)"),
    ("_qty", "integer"),
    ("_status", "text"),
    ("_flag", "text"),
    ("_level", "text"),
]


def _real_column_lookup() -> dict[str, list[tuple[str, str]]]:
    return {
        table["table_name"]: list(table["columns"])  # type: ignore[arg-type]
        for table in REAL_TABLES
    }


def _type_for_metadata_name(name: str) -> str:
    for suffix, sql_type in METADATA_SUFFIXES:
        if name.endswith(suffix):
            return sql_type
    return "text"


def _build_metadata_assets() -> list[dict[str, Any]]:
    real_columns = _real_column_lookup()
    used: set[str] = {column for columns in real_columns.values() for column, _ in columns}
    used.add("batch_no")

    assets: list[dict[str, Any]] = []

    # 3 张刻意重复表：复制真实表列定义（可改名/追加列）
    for designed in DESIGNED_DUPLICATES:
        source = real_columns[designed["copy_columns_from"]]
        rename: dict[str, str] = designed.get("rename") or {}
        columns = [(rename.get(name, name), sql_type) for name, sql_type in source]
        columns.extend(designed.get("extra_columns") or [])
        for name, _ in columns:
            used.add(name)
        assets.append(
            {
                "table_name": designed["table_name"],
                "layer": designed["layer"],
                "domain": designed["domain"],
                "owner": designed["owner"],
                "description": designed["description"],
                "columns": columns,
            }
        )

    # 34 张普通元数据表：按域从组合词池里顺序取列，全局唯一，互不重叠
    cursors: dict[str, int] = {}
    columns_per_asset = [8] * 5 + [7] * 27 + [6] * 2
    for index, (table_name, layer, domain, owner, description) in enumerate(METADATA_THEMES):
        bases = METADATA_BASES[domain]
        total_combos = len(bases) * len(METADATA_SUFFIXES)
        columns: list[tuple[str, str]] = []
        while len(columns) < columns_per_asset[index]:
            cursor = cursors.get(domain, 0)
            base = bases[cursor % len(bases)]
            suffix, sql_type = METADATA_SUFFIXES[(cursor // len(bases)) % len(METADATA_SUFFIXES)]
            cursors[domain] = (cursor + 1) % total_combos
            name = f"{base}{suffix}"
            if name in used:
                continue
            used.add(name)
            columns.append((name, sql_type))
        assets.append(
            {
                "table_name": table_name,
                "layer": layer,
                "domain": domain,
                "owner": owner,
                "description": f"{description}（仅目录元数据，未采样）",
                "columns": columns,
            }
        )
    return assets


# ------------------------------------------------------------- 资产汇总 ----
def build_catalog() -> dict[str, Any]:
    """返回 seed 需要的全部确定性数据。"""
    sample_tables = build_sample_tables()
    assets: list[dict[str, Any]] = []

    for index, table in enumerate(REAL_TABLES):
        assets.append(
            {
                "asset_key": f"{table['layer']}.{table['table_name']}",
                "schema_name": table["layer"],
                "table_name": table["table_name"],
                "layer": table["layer"],
                "domain": table["domain"],
                "owner_name": table["owner"],
                "description": table["description"],
                "row_count": 0,  # 等待 Celery 采集后写入真实行数
                "source_kind": "sample_table",
                "sample_schema": "sample",
                "sample_table": table["table_name"],
                "updated_at": datetime(2026, 11, 9, 2, 0, 0),
                "columns": [
                    {"column_name": name, "data_type": sql_type, "nullable": True, "comment": ""}
                    for name, sql_type in table["columns"]
                ],
            }
        )

    for index, meta in enumerate(_build_metadata_assets()):
        assets.append(
            {
                "asset_key": f"{meta['layer']}.{meta['table_name']}",
                "schema_name": meta["layer"],
                "table_name": meta["table_name"],
                "layer": meta["layer"],
                "domain": meta["domain"],
                "owner_name": meta["owner"],
                "description": meta["description"],
                "row_count": (index + 3) * 2471,  # 元数据行数估算（无样例数据）
                "source_kind": "catalog_metadata",
                "sample_schema": None,
                "sample_table": None,
                "updated_at": datetime(2026, 11, 8, 1, 30, 0),
                "columns": [
                    {
                        "column_name": name,
                        "data_type": sql_type,
                        "nullable": True,
                        "comment": "目录元数据导入",
                    }
                    for name, sql_type in meta["columns"]
                ],
            }
        )

    total_columns = sum(len(asset["columns"]) for asset in assets)
    return {
        "assets": assets,
        "sample_tables": sample_tables,
        "expected": {
            "assets": len(assets),
            "columns": total_columns,
            "sample_rows": ROW_COUNT * len(REAL_TABLES),
        },
    }


# --------------------------------------------------------- 标签 / 任务 ----
TAG_SEED: list[dict[str, Any]] = [
    {
        "table_name": "ods_crm_customer",
        "column_name": "mobile_no",
        "tag_name": "sensitive:high",
        "category": "pii",
        "source": "inferred",
        "confidence": 0.97,
    },
    {
        "table_name": "ods_member_contact",
        "column_name": "cert_no",
        "tag_name": "sensitive:high",
        "category": "pii",
        "source": "inferred",
        "confidence": 0.99,
    },
    {
        "table_name": "ods_crm_customer",
        "column_name": "email_addr",
        "tag_name": "sensitive:medium",
        "category": "pii",
        "source": "inferred",
        "confidence": 0.94,
    },
    {
        "table_name": "dws_member_profile",
        "column_name": "mobile",
        "tag_name": "pii:phone",
        "category": "pii",
        "source": "manual",
        "confidence": 1.0,
    },
    {
        "table_name": "dws_member_profile",
        "column_name": "email",
        "tag_name": "pii:email",
        "category": "pii",
        "source": "manual",
        "confidence": 1.0,
    },
    {
        "table_name": "dws_member_profile",
        "column_name": "total_amount",
        "tag_name": "business:metric",
        "category": "business",
        "source": "inferred",
        "confidence": 0.88,
    },
    {
        "table_name": "ods_crm_customer",
        "column_name": "member_level",
        "tag_name": "business:dimension",
        "category": "business",
        "source": "inferred",
        "confidence": 0.82,
    },
    {
        "table_name": "ods_member_contact",
        "column_name": "mail_box",
        "tag_name": "governance:pending_review",
        "category": "governance",
        "source": "manual",
        "confidence": 1.0,
    },
]

JOB_SEED: list[dict[str, Any]] = [
    {
        "job_name": "月度目录元数据全量同步",
        "connection_name": "hive-metastore-catalog",
        "scope": "37 张仅元数据资产",
        "status": "completed",
        "stats": {"tables_synced": 37, "mode": "catalog_metadata", "duration_seconds": 12},
        "started_hours_ago": 30.0,
        "finished_hours_ago": 29.9,
        "triggered_by": "admin@catmap.demo",
    },
    {
        "job_name": "门店销售域样例采样采集",
        "connection_name": "pg-catmap-sample",
        "scope": "dwd_sales_store_day · dwd_store_sales_daily",
        "status": "running",
        "stats": {"tables_synced": 0},
        "started_minutes_ago": 6,
        "triggered_by": "admin@catmap.demo",
    },
    {
        "job_name": "会员域在线库增量采集",
        "connection_name": "mysql-crm-prod",
        "scope": "ods_crm_customer · ods_member_contact",
        "status": "failed",
        "stats": {"tables_synced": 0},
        "error_code": "conn_timeout",
        "error_message": "连接 mysql-crm-prod 超时（15s），已重试 3 次，建议检查网络白名单",
        "started_hours_ago": 5.0,
        "finished_hours_ago": 4.9,
        "triggered_by": "admin@catmap.demo",
    },
]
