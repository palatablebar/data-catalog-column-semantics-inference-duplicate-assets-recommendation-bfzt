"""分页工具。"""
from __future__ import annotations

from dataclasses import dataclass

from src.constants.limits import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


@dataclass(slots=True)
class Page:
    offset: int
    limit: int

    @property
    def page(self) -> int:
        return self.offset // self.limit + 1


def parse_page(page: int | None, page_size: int | None) -> Page:
    size = min(max(page_size or DEFAULT_PAGE_SIZE, 1), MAX_PAGE_SIZE)
    index = max(page or 1, 1)
    return Page(offset=(index - 1) * size, limit=size)


def page_payload(page: Page, total: int, items: list) -> dict:
    return {
        "items": items,
        "total": total,
        "page": page.page,
        "page_size": page.limit,
    }
