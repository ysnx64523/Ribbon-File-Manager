"""Sorting primitives for directory listings.

Sorting always keeps directories first which is what most file managers do.
"""

from __future__ import annotations

from typing import Callable

from .files import FileEntry

SORT_KEYS: dict[str, Callable[[FileEntry], object]] = {
    "name": lambda e: (not e.is_dir, e.display_name.lower()),
    "size": lambda e: (not e.is_dir, e.size),
    "type": lambda e: (not e.is_dir, e.content_type or e.display_name.lower()),
    "mtime": lambda e: (not e.is_dir, e.mtime),
}


def make_key(column: str) -> Callable[[FileEntry], object]:
    return SORT_KEYS.get(column, SORT_KEYS["name"])
