import asyncio
from app.tools import ALL_TOOLS, MAIN_TOOLS, MARKETPLACE_TOOLS, THIRD_PARTY_TOOLS

def test_all_tools_list_not_empty():
    assert len(ALL_TOOLS) == 73

def test_no_duplicate_tools():
    assert len(ALL_TOOLS) == len(set(ALL_TOOLS))

def test_register_all_tools_no_errors(mcp_with_tools):
    """All 73 tool modules import and register without raising."""
    tools = asyncio.run(mcp_with_tools.list_tools())
    registered_names = {t.name for t in tools}
    assert len(registered_names) >= len(ALL_TOOLS), (
        f"Expected >= {len(ALL_TOOLS)} tools, got {len(registered_names)}. "
        f"Missing: {set(ALL_TOOLS) - registered_names}"
    )

def test_tool_categories_sum():
    assert len(MAIN_TOOLS) + len(MARKETPLACE_TOOLS) + len(THIRD_PARTY_TOOLS) == len(ALL_TOOLS)
