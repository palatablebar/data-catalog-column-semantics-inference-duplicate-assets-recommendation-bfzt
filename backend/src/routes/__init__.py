"""路由总装配（同一份路由在 /api 与根路径各挂一次，兼容 Nginx 剥前缀）。"""
from fastapi import APIRouter

from src.routes import assets, auth, columns, duplicates, health, ingest, meta, tags

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(assets.router)
api_router.include_router(columns.router)
api_router.include_router(duplicates.router)
api_router.include_router(tags.router)
api_router.include_router(ingest.router)
api_router.include_router(meta.router)

__all__ = ["api_router"]
