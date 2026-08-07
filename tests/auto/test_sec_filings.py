# tests/auto/test_sec_filings.py
"""respx-backed tests for the SEC Filings tool.

Unlike test_tools.py (which mocks ``make_request``), these drive the tool through the real
api_client → httpx path with respx intercepting the HTTP call, so they assert the URL and
query parameters that actually leave the process for each of the four endpoints.
"""

import pytest
import respx
from app.tools import sec_filings
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from httpx import Response


async def _invoke_tool(mcp, name, args):
    """Call a tool on the FastMCP instance, compatible with all versions."""
    if hasattr(mcp, "call_tool"):
        result = await mcp.call_tool(name, args)
    else:
        result = await mcp._call_tool(name, args)
    if hasattr(result, "content"):
        return list(result.content)
    return list(result)


@pytest.fixture
def mcp():
    server = FastMCP("manual")
    sec_filings.register(server)
    return server


@pytest.mark.asyncio
@respx.mock
async def test_overview_url_no_pagination(mcp):
    """Overview: /sec-filings/{symbol}, no page[...] params."""
    route = respx.get(url__startswith="https://eodhd.com/api/sec-filings/AAPL.US").mock(
        return_value=Response(200, json={"data": {"ticker": "AAPL.US", "filings": {}}, "meta": {}, "links": {}})
    )
    await _invoke_tool(mcp, "get_sec_filings", {"symbol": "AAPL.US"})

    assert route.called
    request = route.calls.last.request
    assert request.url.path == "/api/sec-filings/AAPL.US"
    assert "page[limit]" not in request.url.params
    assert "page[offset]" not in request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_10k_url_and_pagination(mcp):
    """10-K: /sec-filings/{symbol}/10k with page[limit]/page[offset]."""
    route = respx.get(url__startswith="https://eodhd.com/api/sec-filings/AAPL/10k").mock(
        return_value=Response(200, json={"data": [], "meta": {"total": 0}, "links": {"next": None}})
    )
    await _invoke_tool(mcp, "get_sec_filings", {"symbol": "AAPL", "form": "10k", "limit": 100, "offset": 20})

    assert route.called
    request = route.calls.last.request
    assert request.url.path == "/api/sec-filings/AAPL/10k"
    assert request.url.params.get("page[limit]") == "100"
    assert request.url.params.get("page[offset]") == "20"


@pytest.mark.asyncio
@respx.mock
async def test_10q_url(mcp):
    """10-Q: /sec-filings/{symbol}/10q."""
    route = respx.get(url__startswith="https://eodhd.com/api/sec-filings/TSLA.US/10q").mock(
        return_value=Response(200, json={"data": [], "meta": {}, "links": {}})
    )
    await _invoke_tool(mcp, "get_sec_filings", {"symbol": "TSLA.US", "form": "10q"})

    assert route.called
    assert route.calls.last.request.url.path == "/api/sec-filings/TSLA.US/10q"


@pytest.mark.asyncio
@respx.mock
async def test_8k_url_flexible_form_spelling(mcp):
    """8-K: '8-K' is normalized to the '8k' path segment."""
    route = respx.get(url__startswith="https://eodhd.com/api/sec-filings/AAPL.US/8k").mock(
        return_value=Response(200, json={"data": [], "meta": {}, "links": {}})
    )
    await _invoke_tool(mcp, "get_sec_filings", {"symbol": "AAPL.US", "form": "8-K", "limit": 5})

    assert route.called
    request = route.calls.last.request
    assert request.url.path == "/api/sec-filings/AAPL.US/8k"
    assert request.url.params.get("page[limit]") == "5"


@pytest.mark.asyncio
async def test_invalid_form_raises(mcp):
    with pytest.raises(ToolError, match=r"(?i)form"):
        await _invoke_tool(mcp, "get_sec_filings", {"symbol": "AAPL.US", "form": "10x"})


@pytest.mark.asyncio
async def test_empty_symbol_raises(mcp):
    with pytest.raises(ToolError, match=r"(?i)required"):
        await _invoke_tool(mcp, "get_sec_filings", {"symbol": ""})
