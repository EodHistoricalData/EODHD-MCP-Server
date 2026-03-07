#get_mp_tradinghours_list_markets.py

import json
from typing import Optional
from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


ALLOWED_GROUPS = {"core", "extended", "all", "allowed"}


def _q(key: str, val: Optional[str | int]) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_tradinghours_list_markets(
        group: Optional[str] = None,           # core, extended, all, allowed (default: all)
        api_token: Optional[str] = None,       # per-call override
    ) -> str:
        """
        [TradingHours] List all tracked global markets and exchanges. Use as the starting point
        to browse available markets before looking up details or checking status.
        Returns FinID, exchange name, MIC code, asset type, and group for each market.
        Filter by group: 'core' (24 G20+ markets), 'extended', 'all', or 'allowed' (your tier).
        To search markets by name/country, use get_mp_tradinghours_lookup_markets.
        For detailed info on one market, use get_mp_tradinghours_market_details.
        Consumes 10 API calls per request.

        Args:
            group (str, optional): Filter markets — 'core' (G20+), 'extended' (global equities),
                'all' (equities + derivatives), 'allowed' (your tier). Default: 'all'.
            api_token (str, optional): Per-call token override; env token used otherwise.
        """
        if group is not None:
            group = group.strip().lower()
            if group not in ALLOWED_GROUPS:
                raise ToolError(f"Invalid 'group'. Allowed: {sorted(ALLOWED_GROUPS)}")

        url = f"{EODHD_API_BASE}/mp/tradinghours/markets?1=1"
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
