#get_mp_tradinghours_market_details.py

import json
from typing import Optional
from urllib.parse import quote_plus

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)


def _q(key: str, val: Optional[str | int]) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_tradinghours_market_details(
        fin_id: str,                           # e.g. "us.nyse"
        api_token: Optional[str] = None,       # per-call override
    ) -> str:
        """
        Marketplace: TradingHours — Get Market Details
        GET /api/mp/tradinghours/markets/details

        Returns detailed information for a specific market identified by its FinID.

        Args:
            fin_id (str): Market FinID, case-insensitive (e.g. 'us.nyse', 'gb.lse').
            api_token (str, optional): Per-call token override; env token used otherwise.

        Notes:
            - Marketplace product: 10 API calls per request.
            - Response fields: fin_id, country_code, exchange, market, products, mic,
              mic_extended, acronym, asset_type, memo, permanently_closed, timezone,
              weekend_definition, holidays_min_date, holidays_max_date.
            - Returns IANA timezone identifiers.
        """
        if not fin_id or not isinstance(fin_id, str):
            return _err(
                "Parameter 'fin_id' is required (e.g. 'us.nyse')."
            )

        url = f"{EODHD_API_BASE}/mp/tradinghours/markets/details?1=1"
        url += _q("fin_id", fin_id.strip())
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
