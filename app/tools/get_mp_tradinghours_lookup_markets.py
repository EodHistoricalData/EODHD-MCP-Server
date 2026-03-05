#get_mp_tradinghours_lookup_markets.py

import json
from typing import Optional
from urllib.parse import quote_plus

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


ALLOWED_GROUPS = {"core", "extended", "all", "allowed"}


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)


def _q(key: str, val: Optional[str | int]) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_tradinghours_lookup_markets(
        q: Optional[str] = None,              # free-form search term
        group: Optional[str] = None,           # core, extended, all, allowed (default: all)
        api_token: Optional[str] = None,       # per-call override
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
                return _err(f"Invalid 'group'. Allowed: {sorted(ALLOWED_GROUPS)}")

        url = f"{EODHD_API_BASE}/mp/tradinghours/markets/lookup?1=1"
        if q:
            url += _q("q", q.strip())
        if group:
            url += _q("group", group)
        if api_token:
            url += _q("api_token", api_token)

        data = await make_request(url)

        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected response format from API.")
