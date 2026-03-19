import os

os.environ.setdefault("EODHD_API_KEY", "test_key_for_ci")

import pytest
from app.tools import register_all as register_all_tools
from fastmcp import FastMCP


@pytest.fixture
def bare_mcp():
    """A bare FastMCP instance with no tools registered."""
    return FastMCP("test")


@pytest.fixture
def mcp_with_tools():
    """FastMCP with all tools registered."""
    server = FastMCP("test")
    register_all_tools(server)
    return server
