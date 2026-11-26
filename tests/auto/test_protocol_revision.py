"""MCP protocol revisions over the real streamable-HTTP app, as raw JSON-RPC.

Revision 2026-07-28 is reached through `server/discover` and a per-request `_meta`
envelope; `initialize` can only negotiate up to 2025-11-25 by design. Older clients
must keep negotiating their own revision and getting data.
"""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest
import respx
from app import protocol
from app.config import SERVER_VERSION
from app.prompts import register_all as register_all_prompts
from app.resources import register_all as register_all_resources
from app.telemetry_middleware import install as install_telemetry
from app.tools import register_all as register_all_tools
from fastmcp import FastMCP

MODERN = "2026-07-28"
HANDSHAKE_VERSIONS = ["2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"]
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "X-API-Key": "test_key_for_ci",
}
ENVELOPE = {
    "io.modelcontextprotocol/protocolVersion": MODERN,
    "io.modelcontextprotocol/clientCapabilities": {},
    "io.modelcontextprotocol/clientInfo": {"name": "pytest", "version": "0"},
}
CACHE_TTL_MS = protocol.CACHE_TTL_SECONDS * 1000


async def test_discover_negotiates_the_new_revision(client):
    result = await _modern(client, "server/discover", {})

    assert MODERN in result["supportedVersions"]
    assert result["resultType"] == "complete"
    assert result["ttlMs"] == CACHE_TTL_MS
    assert result["cacheScope"] == "public"
    assert result["_meta"]["io.modelcontextprotocol/serverInfo"]["version"] == SERVER_VERSION
    assert "logging" not in result["capabilities"]
    assert {"tools", "resources", "prompts"} <= set(result["capabilities"])


@pytest.mark.parametrize(
    ("method", "params"),
    [
        ("tools/list", {}),
        ("resources/list", {}),
        ("resources/templates/list", {}),
        ("prompts/list", {}),
        ("resources/read", {"uri": "eodhd://references/README"}),
    ],
)
async def test_cacheable_results_carry_cache_hints(client, method, params):
    result = await _modern(client, method, params, name=params.get("uri"))

    assert result["ttlMs"] == CACHE_TTL_MS
    assert result["cacheScope"] == "public"
    assert result["resultType"] == "complete"


async def test_modern_tool_call_returns_data(client):
    result = await _modern(
        client,
        "tools/call",
        {"name": "get_live_price_data", "arguments": {"ticker": "AAPL.US"}},
        name="get_live_price_data",
    )

    assert result["isError"] is False
    assert "AAPL.US" in json.dumps(result["content"])


@pytest.mark.parametrize("version", HANDSHAKE_VERSIONS)
async def test_older_clients_keep_their_revision_and_get_data(client, server, version):
    init = await _rpc(
        client,
        "initialize",
        {"protocolVersion": version, "capabilities": {}, "clientInfo": {"name": "pytest", "version": "0"}},
    )

    assert init["protocolVersion"] == version
    assert init["serverInfo"]["version"] == SERVER_VERSION
    assert "logging" not in init["capabilities"]

    headers = {"MCP-Protocol-Version": version}
    tools = await _rpc(client, "tools/list", {}, headers)
    call = await _rpc(
        client, "tools/call", {"name": "get_live_price_data", "arguments": {"ticker": "AAPL.US"}}, headers
    )

    assert len(tools["tools"]) == len(await server.list_tools())
    assert call["isError"] is False
    assert "AAPL.US" in json.dumps(call["content"])


async def test_a_request_without_the_protocol_header_is_still_served(client):
    """Clients from before 2025-06-18 do not send MCP-Protocol-Version after initialize."""
    call = await _rpc(client, "tools/call", {"name": "get_live_price_data", "arguments": {"ticker": "AAPL.US"}})

    assert call["isError"] is False


async def test_both_eras_list_the_same_tools(client):
    modern = await _modern(client, "tools/list", {})
    legacy = await _rpc(client, "tools/list", {}, {"MCP-Protocol-Version": "2025-11-25"})

    assert sorted(t["name"] for t in modern["tools"]) == sorted(t["name"] for t in legacy["tools"])


@pytest.fixture
def server():
    mcp = FastMCP("eodhd-datasets", **protocol.server_options())
    protocol.install(mcp)
    install_telemetry(mcp)
    register_all_tools(mcp)
    register_all_resources(mcp)
    register_all_prompts(mcp)

    return mcp


@pytest.fixture
def client(server):
    return _HttpClient(server)


class _HttpClient:
    """Opens the real HTTP app per request, inside the test's own task (anyio needs that)."""

    def __init__(self, server: FastMCP):
        self._server = server

    async def post(self, path: str, **kwargs) -> httpx.Response:
        async with _http(self._server) as http:
            return await http.post(path, **kwargs)


@asynccontextmanager
async def _http(server: FastMCP) -> AsyncIterator[httpx.AsyncClient]:
    app = server.http_app(path="/mcp", stateless_http=True)
    with respx.mock(assert_all_called=False) as router:
        router.route(host="eodhd.com").mock(return_value=httpx.Response(200, json={"code": "AAPL.US", "close": 1.5}))
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http,
        ):
            yield http


async def _modern(client: "_HttpClient", method: str, params: dict, name: str | None = None) -> dict:
    headers = {"Mcp-Method": method, "MCP-Protocol-Version": MODERN}
    if name:
        headers["Mcp-Name"] = name

    return await _rpc(client, method, {**params, "_meta": ENVELOPE}, headers)


async def _rpc(client: "_HttpClient", method: str, params: dict, headers: dict | None = None) -> dict:
    response = await client.post(
        "/mcp",
        headers={**HEADERS, **(headers or {})},
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )
    assert response.status_code == 200, response.text

    payload = _payload(response.text)
    assert "error" not in payload, payload

    return payload["result"]


def _payload(text: str) -> dict:
    if text.startswith("event:"):
        text = next(line[len("data:") :] for line in text.splitlines() if line.startswith("data:"))

    return json.loads(text)
