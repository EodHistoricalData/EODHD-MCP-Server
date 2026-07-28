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


# A numeric id is what an agent gets handed by the README page, so an id must keep pointing at
# the same document across releases. New pages are appended; these anchors prove nothing shifted.
STABLE_ANCHORS = {
    (2, 1): "bulk-fundamentals.md",
    (2, 24): "investverte-esg-list-companies.md",
    (2, 49): "sanctions-entities.md",
    (2, 52): "sanctions-vessels.md",
    (2, 78): "websockets-realtime.md",
    (2, 79): "real-estate-countries.md",
    (1, 1): "free.md",
    (3, 1): "api-authentication-demo-access.md",
}


@pytest.mark.parametrize(("anchor", "filename"), sorted(STABLE_ANCHORS.items()))
def test_registry_ids_are_stable(anchor, filename):
    page_type, page_id = anchor

    assert _PAGE_REGISTRY[page_type][page_id][1] == filename, (
        f"id {page_id} of type {page_type} now points at "
        f"{_PAGE_REGISTRY[page_type][page_id][1]} — renumbering silently changes what an agent reads; "
        "append new pages instead"
    )
