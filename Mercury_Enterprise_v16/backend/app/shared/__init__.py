"""Shared AEOS primitives used by every Mercury package.

Canonical home for ActorContext, pagination, and HTTP query helpers so domain
modules do not redefine them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field

T = TypeVar("T")

MAX_PAGE = 500
DEFAULT_PAGE = 100


@dataclass(frozen=True)
class ActorContext:
    """Session-derived identity used for org scoping and audit across domains."""

    username: str
    role: str
    organization_id: str
    site_id: str = ""


class PageParams(BaseModel):
    limit: int = Field(default=DEFAULT_PAGE, ge=1, le=MAX_PAGE)
    offset: int = Field(default=0, ge=0)


def clamp_page(limit: int | None = None, offset: int | None = None) -> tuple[int, int]:
    lim = DEFAULT_PAGE if limit is None else int(limit)
    off = 0 if offset is None else int(offset)
    return min(max(lim, 1), MAX_PAGE), max(off, 0)


def page_query(
    limit: int = Query(DEFAULT_PAGE, ge=1, le=MAX_PAGE),
    offset: int = Query(0, ge=0),
) -> PageParams:
    return PageParams(limit=limit, offset=offset)


class Page(BaseModel):
    """Optional envelope for list endpoints that need total counts."""

    items: list
    total: int | None = None
    limit: int
    offset: int


def require_non_empty(value: str | None, *, field: str) -> str:
    text = (value or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail=f"{field} is required")
    return text
