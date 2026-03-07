# get_mp_tradinghours_lookup_markets.py

import json
from urllib.parse import quote_plus

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

ALLOWED_GROUPS = {"core", "extended", "all", "allowed"}


def _q(key: str, val: str | int | None) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_tradinghours_lookup_markets(
        q: str | None = None,  # free-form search term
        group: str | None = None,  # core, extended, all, allowed (default: all)
        api_token: str | None = None,  # per-call override
    ) -> str:
        """
        Marketplace: TradingHours — Lookup Markets
        GET /api/mp/tradinghours/markets/lookup

        Search for markets by name, MIC, country, or any free-form term.

        Args:
            q (str, optional): Free-form search query (exchange name, market name, MIC,
                country). Omit to return all markets.
            group (str, optional): Filter results — 'core', 'extended', 'all', 'allowed'.
                Default: 'all'.
            api_token (str, optional): Per-call token override; env token used otherwise.

        Notes:
            - Marketplace product: 10 API calls per request.
            - Over 900 different trading schedules tracked.
            - Omitting 'q' returns all markets (like list endpoint).
        """
        if group is not None:
            group = group.strip().lower()
            if group not in ALLOWED_GROUPS:
                raise ToolError(f"Invalid 'group'. Allowed: {sorted(ALLOWED_GROUPS)}")

        url = f"{EODHD_API_BASE}/mp/tradinghours/markets/lookup?1=1"
        if q:
            url += _q("q", q.strip())
        if group:
            url += _q("group", group)
        if api_token:
            url += _q("api_token", api_token)

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
