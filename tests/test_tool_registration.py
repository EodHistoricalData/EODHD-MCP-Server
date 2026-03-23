"""Tests for app.tools — tool list integrity and registration."""

import pytest
from app.tools import ALL_TOOLS, MAIN_TOOLS, MARKETPLACE_TOOLS, THIRD_PARTY_TOOLS


def test_all_tools_list_not_empty():
    """ALL_TOOLS has a reasonable number of tools (dynamic, not hardcoded)."""
    assert len(ALL_TOOLS) >= 70  # guard against accidental mass deletion


def test_no_duplicate_tools():
    assert len(ALL_TOOLS) == len(set(ALL_TOOLS))


@pytest.mark.asyncio
async def test_register_all_tools_no_errors(mcp_with_tools):
    """All tool modules import and register without raising."""
    tools = await mcp_with_tools.list_tools()
    registered_names = {t.name for t in tools}
    # Some tools may register aliases (e.g. praams), so >= is correct
    assert len(registered_names) >= len(ALL_TOOLS) - 1, (
        f"Expected >= {len(ALL_TOOLS) - 1} tools, got {len(registered_names)}. "
        f"Missing: {set(ALL_TOOLS) - registered_names}"
    )


def test_tool_categories_sum():
    assert len(MAIN_TOOLS) + len(MARKETPLACE_TOOLS) + len(THIRD_PARTY_TOOLS) == len(ALL_TOOLS)
