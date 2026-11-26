# tests/auto/test_etf_holdings.py
"""respx-backed tests for the ETF Holdings tools (get_etf_holdings, get_etf_held_by).

Like test_sec_filings.py, these go through the real api_client -> httpx path, so they assert the URL
and query parameters that leave the process, and how coded API errors reach the agent.
"""

import json

import pytest
import respx
from app.tools import get_etf_held_by, get_etf_holdings
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from httpx import Response

HOLDINGS_BODY = {
    "data": {
        "General": {"Code": "XLE", "Type": "ETF", "Exchange": "US", "Source": "nport", "Is_Complete": True},
        "Holdings": {"XOM.US": {"Code": "XOM", "Name": "Exxon Mobil Corp", "Assets_%": 22.5}},
        "Top_10_Holdings": {"XOM.US": {"Code": "XOM", "Name": "Exxon Mobil Corp", "Assets_%": 22.5}},
        "Holdings_Count": 1,
        "Asset_Allocation": {},
        "Sector_Weights": {},
        "World_Regions": {},
        "Performance": None,
    },
    "meta": [],
    "links": [],
}

HELD_BY_BODY = {
    "data": {
        "security": {"ticker": "NVDA", "exchange": "US", "name": "NVIDIA Corp"},
        "held_by_count": 1,
        "funds": [
            {
                "ticker": "SMH",
                "name": "VanEck Semiconductor ETF",
                "weight": 20.1,
                "shares": 100,
                "value_usd": 1000,
                "report_date": "2026-09-30",
            }
        ],
    },
    "meta": {"total": 1, "offset": 0, "limit": 3},
    "links": {"next": None},
}


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
    get_etf_holdings.register(server)
    get_etf_held_by.register(server)
    return server


@pytest.mark.asyncio
@respx.mock
async def test_holdings_url_has_no_pagination_or_fmt(mcp):
    route = respx.get(url__startswith="https://eodhd.com/api/etf/holdings/XLE.US").mock(
        return_value=Response(200, json=HOLDINGS_BODY)
    )
    await _invoke_tool(mcp, "get_etf_holdings", {"ticker": "XLE.US"})

    assert route.called
    request = route.calls.last.request
    assert request.url.path == "/api/etf/holdings/XLE.US"
    assert "page[limit]" not in request.url.params
    assert "page[offset]" not in request.url.params
    assert "fmt" not in request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_holdings_accepts_bare_ticker(mcp):
    route = respx.get(url__startswith="https://eodhd.com/api/etf/holdings/VTI").mock(
        return_value=Response(200, json=HOLDINGS_BODY)
    )
    await _invoke_tool(mcp, "get_etf_holdings", {"ticker": " VTI "})

    assert route.calls.last.request.url.path == "/api/etf/holdings/VTI"


@pytest.mark.asyncio
@respx.mock
async def test_holdings_empty_list_holdings_is_returned(mcp):
    """A fund with no positions returns Holdings as [] rather than an object."""
    body = {"data": {**HOLDINGS_BODY["data"], "Holdings": [], "Holdings_Count": 0}, "meta": [], "links": []}
    respx.get(url__startswith="https://eodhd.com/api/etf/holdings/GAID").mock(return_value=Response(200, json=body))

    result = await _invoke_tool(mcp, "get_etf_holdings", {"ticker": "GAID"})

    item = result[0]
    # v1 returns an embedded resource, v2 returns plain text content.
    text = item.resource.text if hasattr(item, "resource") else item.text
    payload = json.loads(text)
    assert payload["data"]["Holdings"] == []


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("code", ["FUND_NOT_FOUND", "NOT_COVERED", "NO_HOLDINGS_YET"])
async def test_holdings_404_code_reaches_the_agent(mcp, code):
    body = {"errors": [{"status": "404", "title": "Symbol not found", "code": code, "detail": "No data."}]}
    respx.get(url__startswith="https://eodhd.com/api/etf/holdings/GLD").mock(return_value=Response(404, json=body))

    with pytest.raises(ToolError) as exc:
        await _invoke_tool(mcp, "get_etf_holdings", {"ticker": "GLD"})

    assert "404" in str(exc.value)
    assert code in str(exc.value)


@pytest.mark.asyncio
@respx.mock
async def test_holdings_422_for_non_us_ticker(mcp):
    body = {"errors": {"symbol": ["ETF data is available for US-listed securities only."]}}
    respx.get(url__startswith="https://eodhd.com/api/etf/holdings/CSPX.LSE").mock(return_value=Response(422, json=body))

    with pytest.raises(ToolError, match="US-listed securities only"):
        await _invoke_tool(mcp, "get_etf_holdings", {"ticker": "CSPX.LSE"})


@pytest.mark.asyncio
@respx.mock
async def test_held_by_url_and_pagination(mcp):
    route = respx.get(url__startswith="https://eodhd.com/api/etf/security/NVDA/held-by").mock(
        return_value=Response(200, json=HELD_BY_BODY)
    )
    await _invoke_tool(mcp, "get_etf_held_by", {"ticker": "NVDA", "limit": 3, "offset": 6})

    request = route.calls.last.request
    assert request.url.path == "/api/etf/security/NVDA/held-by"
    assert request.url.params["page[limit]"] == "3"
    assert request.url.params["page[offset]"] == "6"
    assert "fmt" not in request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_held_by_omits_pagination_by_default_and_keeps_foreign_suffix(mcp):
    route = respx.get(url__startswith="https://eodhd.com/api/etf/security/ASML.AS/held-by").mock(
        return_value=Response(200, json=HELD_BY_BODY)
    )
    await _invoke_tool(mcp, "get_etf_held_by", {"ticker": "ASML.AS"})

    request = route.calls.last.request
    assert request.url.path == "/api/etf/security/ASML.AS/held-by"
    assert "page[limit]" not in request.url.params
    assert "page[offset]" not in request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_held_by_accepts_limit_up_to_5000(mcp):
    route = respx.get(url__startswith="https://eodhd.com/api/etf/security/XOM/held-by").mock(
        return_value=Response(200, json=HELD_BY_BODY)
    )
    await _invoke_tool(mcp, "get_etf_held_by", {"ticker": "XOM", "limit": 5000})

    assert route.calls.last.request.url.params["page[limit]"] == "5000"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("args", "pattern"),
    [
        ({"ticker": "NVDA", "limit": 5001}, "(?i)limit"),
        ({"ticker": "NVDA", "limit": 0}, "(?i)limit"),
        ({"ticker": "NVDA", "offset": -1}, "(?i)offset"),
        ({"ticker": "  "}, "(?i)ticker"),
    ],
)
async def test_held_by_validation(mcp, args, pattern):
    with pytest.raises(ToolError, match=pattern):
        await _invoke_tool(mcp, "get_etf_held_by", args)


@pytest.mark.asyncio
@respx.mock
async def test_held_by_404_without_code_is_an_error(mcp):
    body = {"errors": [{"status": "404", "title": "Symbol not found"}]}
    respx.get(url__startswith="https://eodhd.com/api/etf/security/ZZZZ/held-by").mock(
        return_value=Response(404, json=body)
    )

    with pytest.raises(ToolError, match="404"):
        await _invoke_tool(mcp, "get_etf_held_by", {"ticker": "ZZZZ"})


@pytest.mark.asyncio
@respx.mock
async def test_held_by_403_for_demo_token_says_plan(mcp):
    respx.get(url__startswith="https://eodhd.com/api/etf/security/NVDA/held-by").mock(
        return_value=Response(403, text="Forbidden")
    )

    with pytest.raises(ToolError, match="403"):
        await _invoke_tool(mcp, "get_etf_held_by", {"ticker": "NVDA", "api_token": "demo"})


@pytest.mark.asyncio
async def test_tools_are_registered_read_only_with_beta_wording(mcp):
    tools = {t.name: t for t in await mcp.list_tools()}

    for name in ("get_etf_holdings", "get_etf_held_by"):
        assert tools[name].annotations.readOnlyHint is True
        description = tools[name].description
        assert "Beta" in description
        assert "US-listed" in description
        assert "10 API calls" in description
    assert "demo token" in tools["get_etf_held_by"].description
