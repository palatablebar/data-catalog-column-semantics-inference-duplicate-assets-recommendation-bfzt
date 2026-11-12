"""目录 CSV 导出：后端生成字节，前端只触发下载。"""
from __future__ import annotations

import csv
import io
from datetime import datetime

from sqlalchemy.orm import Session
from src.services import asset_service


def build_catalog_csv(db: Session) -> tuple[str, bytes]:
    rows = asset_service.export_rows(db)
    header = asset_service.layer_export_header()
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    filename = f"catmap-catalog-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
    return filename, buffer.getvalue().encode("utf-8-sig")
