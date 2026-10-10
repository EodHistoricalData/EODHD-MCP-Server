from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from app.tools.get_fundamentals_data import register as register_fundamentals
from app.tools.get_support_resistance_levels import (
    register as register_support_resistance,
)
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError


async def _invoke_tool(mcp, name, args):
    if hasattr(mcp, "call_tool"):
        result = await mcp.call_tool(name, args)
    else:
        result = await mcp._call_tool(name, args)
    if hasattr(result, "content"):
        return list(result.content)
    return list(result)


@pytest.mark.asyncio
async def test_support_resistance_propagates_upstream_api_error():
    server = FastMCP("manual")
    register_support_resistance(server)

    mock_return = {
        "error": "EODHD API request failed with 401 Unauthorized.",
        "status_code": 401,
        "error_code": "OPERATION_NOT_PERMITTED",
        "upstream_message": "User 12 do not have access to this watch list DJI",
    }

    with patch(
        "app.tools.get_support_resistance_levels.make_request",
        AsyncMock(return_value=mock_return),
    ), pytest.raises(ToolError, match="OPERATION_NOT_PERMITTED"):
        await _invoke_tool(server, "get_support_resistance_levels", {"ticker": "AAPL.US"})


@pytest.mark.asyncio
async def test_fundamentals_propagates_upstream_api_error_from_general():
    server = FastMCP("manual")
    register_fundamentals(server)

    mock_return = {
        "error": "EODHD API request failed with 401 Unauthorized.",
        "status_code": 401,
        "error_code": "OPERATION_NOT_PERMITTED",
        "upstream_message": "General section is not available for this subscription tier",
    }

    with patch(
        "app.tools.get_fundamentals_data.make_request",
        AsyncMock(return_value=mock_return),
    ), pytest.raises(ToolError, match="General section is not available"):
        await _invoke_tool(server, "get_fundamentals_data", {"ticker": "AAPL.US"})


def test_tool_modules_do_not_use_direct_api_error_dict_handling():
    root = Path(__file__).resolve().parents[2] / "app" / "tools"
    disallowed_patterns = [
        'data.get("error")',
        "data['error']",
        'data["error"]',
        'raise ToolError(str(data["error"]))',
        "raise ToolError(str(data['error']))",
    ]

    offenders: list[str] = []
    for path in sorted(root.glob("*.py")):
        text = path.read_text()
        matches = [pattern for pattern in disallowed_patterns if pattern in text]
        if matches:
            offenders.append(f"{path.name}: {', '.join(matches)}")

    assert offenders == []
