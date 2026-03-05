import os
os.environ.setdefault("EODHD_API_KEY", "test_key_for_ci")

import pytest
from fastmcp import FastMCP
from app.tools import register_all as register_all_tools, ALL_TOOLS

@pytest.fixture
def mcp():
    return FastMCP("test")

@pytest.fixture
def mcp_with_tools(mcp):
    register_all_tools(mcp)
    return mcp
