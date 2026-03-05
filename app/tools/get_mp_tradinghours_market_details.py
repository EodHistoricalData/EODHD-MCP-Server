#get_mp_tradinghours_market_details.py

import json
from typing import Optional
from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


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

        Returns:
            JSON object with:
            - fin_id (str): Unique market identifier (e.g. 'us.nyse').
            - exchange (str): Exchange name.
            - market (str): Market name.
            - products (str): Traded product types.
            - timezone (str): IANA timezone identifier.
            - local_time (str): Current local time at the exchange.
            - regular (object): Regular session hours with open/close times.
            - pre_market (object|null): Pre-market session hours, if applicable.
            - post_market (object|null): Post-market session hours, if applicable.
            - holidays (array): Upcoming holidays with date, name, and schedule impact.

        Notes:
            - Marketplace product: 10 API calls per request.
            - Returns IANA timezone identifiers.
        """
        if not fin_id or not isinstance(fin_id, str):
            raise ToolError(
                "Parameter 'fin_id' is required (e.g. 'us.nyse')."
            )

        url = f"{EODHD_API_BASE}/mp/tradinghours/markets/details?1=1"
        url += _q("fin_id", fin_id.strip())
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
