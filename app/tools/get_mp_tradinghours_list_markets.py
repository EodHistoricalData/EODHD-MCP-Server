#get_mp_tradinghours_list_markets.py

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
    async def get_mp_tradinghours_list_markets(
        group: Optional[str] = None,           # core, extended, all, allowed (default: all)
        api_token: Optional[str] = None,       # per-call override
    ) -> str:
        """
        Marketplace: TradingHours — List All Markets
        GET /api/mp/tradinghours/markets

        Returns a list of all tracked markets with metadata.

        Args:
            group (str, optional): Filter markets — 'core' (G20+), 'extended' (global equities),
                'all' (equities + derivatives), 'allowed' (your tier). Default: 'all'.
            api_token (str, optional): Per-call token override; env token used otherwise.

        Notes:
            - Marketplace product: 10 API calls per request.
            - Response fields: fin_id, exchange, market, products, mic, asset_type,
              group, permanently_closed, holidays_min_date, holidays_max_date.
            - Core tier: 24 G20+ markets.
        """
        if group is not None:
            group = group.strip().lower()
            if group not in ALLOWED_GROUPS:
                return _err(f"Invalid 'group'. Allowed: {sorted(ALLOWED_GROUPS)}")

        url = f"{EODHD_API_BASE}/mp/tradinghours/markets?1=1"
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
