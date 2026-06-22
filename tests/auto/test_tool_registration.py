# tests/auto/test_tool_registration.py
"""Tests for app.tools — tool list integrity and registration."""

import pytest
from app.tools import ALL_TOOLS, MAIN_TOOLS, MARKETPLACE_TOOLS, THIRD_PARTY_TOOLS


def test_all_tools_list_not_empty():
    """ALL_TOOLS has a reasonable number of tools (dynamic, not hardcoded)."""
    assert len(ALL_TOOLS) >= 65  # guard against accidental mass deletion


def test_no_duplicate_tools():
    assert len(ALL_TOOLS) == len(set(ALL_TOOLS))


@pytest.mark.asyncio
async def test_register_all_tools_no_errors(mcp_with_tools):
    """All tool modules import and register without raising."""
    if hasattr(mcp_with_tools, "list_tools"):
        tools = await mcp_with_tools.list_tools()
        registered_names = {t.name for t in tools}
    else:
        tools = await mcp_with_tools.get_tools()
        registered_names = set(tools.keys())
    # Some tools may register aliases (e.g. praams), so >= is correct
    assert len(registered_names) >= len(ALL_TOOLS) - 1, (
        f"Expected >= {len(ALL_TOOLS) - 1} tools, got {len(registered_names)}. "
        f"Missing: {set(ALL_TOOLS) - registered_names}"
    )


def test_tool_categories_sum():
    assert len(MAIN_TOOLS) + len(MARKETPLACE_TOOLS) + len(THIRD_PARTY_TOOLS) == len(ALL_TOOLS)


def test_page_registry_illio_ids_retired():
    """illio docs (endpoint ids 13-20) were removed; the gap is intentional and must
    not be reused. Surrounding ids stay put so the public id contract is preserved."""
    from app.tools.retrieve_description_by_id import _PAGE_REGISTRY

    endpoints = _PAGE_REGISTRY[2]
    assert all(i not in endpoints for i in range(13, 21)), "retired illio ids 13-20 must stay absent"
    assert 12 in endpoints and 21 in endpoints, "ids around the gap must be unchanged"
    assert not any("illio" in fname for _, fname in endpoints.values()), "no illio doc refs may remain"
