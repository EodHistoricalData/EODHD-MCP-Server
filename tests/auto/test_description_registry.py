# tests/auto/test_description_registry.py
"""Integrity tests for the retrieve_description_by_id page registry.

This file previously had no coverage; the registry ids were renumbered when the
Illio provider was removed, so these guards lock the invariants in place:
  - within each page type, ids are contiguous starting at 1 (id 0 = README)
  - every registry entry points at a file that actually exists on disk
  - no dropped provider (illio) lingers in the registry
"""

import pytest
from app.tools.retrieve_description_by_id import _PAGE_REGISTRY, _RESOURCES_DIR


@pytest.mark.parametrize("page_type", sorted(_PAGE_REGISTRY))
def test_ids_contiguous_from_one(page_type):
    """Non-README ids must be 1..N with no gaps or duplicates."""
    ids = sorted(k for k in _PAGE_REGISTRY[page_type] if k != 0)
    assert ids == list(range(1, len(ids) + 1)), f"type={page_type} ids are not contiguous 1..N: {ids}"


@pytest.mark.parametrize("page_type", sorted(_PAGE_REGISTRY))
def test_registry_files_exist(page_type):
    """Every (subdir, filename) entry must resolve to a real file."""
    missing = []
    for page_id, (subdir, filename) in _PAGE_REGISTRY[page_type].items():
        if not (_RESOURCES_DIR / subdir / filename).is_file():
            missing.append((page_id, f"{subdir}/{filename}"))
    assert not missing, f"type={page_type} references missing files: {missing}"


def test_no_illio_in_registry():
    """Illio was removed from the server; it must not reappear in the registry."""
    hits = [
        (pt, pid, entry)
        for pt, pages in _PAGE_REGISTRY.items()
        for pid, entry in pages.items()
        if "illio" in str(entry).lower()
    ]
    assert not hits, f"unexpected illio entries in registry: {hits}"
