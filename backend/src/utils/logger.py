"""极简结构化日志。"""
from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def get_logger(name: str) -> logging.Logger:
    global _CONFIGURED
    if not _CONFIGURED:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s %(message)s"))
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.handlers = [handler]
        _CONFIGURED = True
    return logging.getLogger(name)
