# tests/auto/test_tool_registration.py
"""Tests for app.tools — tool list integrity and registration."""

from importlib.metadata import version

import pytest
from app.tools import ALL_TOOLS, MAIN_TOOLS, MARKETPLACE_TOOLS, THIRD_PARTY_TOOLS
from fastmcp import Client

# Tools that trigger provider-side report generation and email delivery, so they are
# deliberately not annotated read-only.
WRITE_TOOLS = {
    "get_mp_praams_report_equity_by_ticker",
    "get_mp_praams_report_equity_by_isin",
    "get_mp_praams_report_bond_by_isin",
}

# Modules that register their tool under a different public name than the module name.
ALIASED_MODULES = {
    "get_mp_index_components": "mp_index_components",
    "get_mp_indices_list": "mp_indices_list",
    "get_mp_praams_smart_investment_screener_bond": "get_mp_praams_smart_screener_bond",
    "get_mp_praams_smart_investment_screener_equity": "get_mp_praams_smart_screener_equity",
    "get_mp_us_options_contracts": "get_us_options_contracts",
    "get_mp_us_options_eod": "get_us_options_eod",
    "get_mp_us_options_underlyings": "get_us_options_underlyings",
    "get_stock_screener_data": "stock_screener",
}


async def _wire_tools(mcp_with_tools) -> list:
    """Return the tools exactly as an MCP client receives them over the protocol."""
    async with Client(mcp_with_tools) as client:
        return list(await client.list_tools())


def test_installed_fastmcp_matches_pin():
    """The title guarantee below depends on the fastmcp version pinned in requirements.txt."""
    installed = tuple(int(part) for part in version("fastmcp").split(".")[:3] if part.isdigit())

    assert installed >= (3, 4, 4), (
        f"fastmcp {version('fastmcp')} is installed but requirements.txt pins >=3.4.4,<3.5; "
        "older versions do not emit the top-level Tool.title the connector directory reads"
    )


def test_all_tools_list_not_empty():
    """ALL_TOOLS has a reasonable number of tools (dynamic, not hardcoded)."""
    assert len(ALL_TOOLS) >= 80  # guard against accidental mass deletion


def test_no_duplicate_tools():
    assert len(ALL_TOOLS) == len(set(ALL_TOOLS))


@pytest.mark.asyncio
async def test_register_all_tools_no_errors(mcp_with_tools):
    """Every module in ALL_TOOLS registers its tool under the expected public name."""
    registered = {tool.name for tool in await _wire_tools(mcp_with_tools)}
    expected = {ALIASED_MODULES.get(module, module) for module in ALL_TOOLS}

    assert not expected - registered, f"modules that registered nothing: {sorted(expected - registered)}"
    assert not registered - expected, f"unexpected extra tools registered: {sorted(registered - expected)}"


def test_tool_categories_sum():
    assert len(MAIN_TOOLS) + len(MARKETPLACE_TOOLS) + len(THIRD_PARTY_TOOLS) == len(ALL_TOOLS)


@pytest.mark.asyncio
async def test_every_tool_exposes_a_title(mcp_with_tools):
    """Both the canonical MCP field and the legacy annotation must carry the display name."""
    problems = []
    for tool in await _wire_tools(mcp_with_tools):
        annotation_title = tool.annotations.title if tool.annotations else None
        if not tool.title or not annotation_title or tool.title != annotation_title:
            problems.append((tool.name, tool.title, annotation_title))

    assert not problems, f"tools with a missing or inconsistent title: {problems}"


@pytest.mark.asyncio
async def test_read_only_hint_matches_tool_behaviour(mcp_with_tools):
    """Read-only hints must be accurate: report tools have provider-side side effects."""
    wrong = []
    for tool in await _wire_tools(mcp_with_tools):
        hint = tool.annotations.readOnlyHint if tool.annotations else None
        expected = tool.name not in WRITE_TOOLS
        if hint is not expected:
            wrong.append((tool.name, hint, expected))

    assert not wrong, f"tools with a wrong readOnlyHint (name, actual, expected): {wrong}"
