#get_mp_tradinghours_market_status.py

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
    async def get_mp_tradinghours_market_status(
        fin_id: str,                           # e.g. "us.nyse"
        api_token: Optional[str] = None,       # per-call override
    ) -> str:
        """
        Marketplace: TradingHours — Market Status
        GET /api/mp/tradinghours/markets/status

        Returns real-time open/closed status for a specific market.

        Args:
            fin_id (str): Market FinID, case-insensitive (e.g. 'us.nyse').
            api_token (str, optional): Per-call token override; env token used otherwise.

        Returns:
            JSON object with:
            - fin_id (str): Unique market identifier.
            - exchange (str): Exchange name.
            - market (str): Market name.
            - status (str): Current status — 'Open' or 'Closed'.
            - reason (str): Reason for current status (e.g. 'Primary Trading Session', 'After-Hours').
            - local_time (str): Current local time at the exchange.
            - next_bell_action (str): Next expected action ('open' or 'close').
            - next_bell_time_utc (str): UTC timestamp of next bell event.

        Notes:
            - Marketplace product: 10 API calls per request.
            - Does NOT include circuit breakers or trading halts.
            - Cache-friendly: use the 'until' field to know when to re-check.
        """
        if not fin_id or not isinstance(fin_id, str):
            raise ToolError(
                "Parameter 'fin_id' is required (e.g. 'us.nyse')."
            )

        url = f"{EODHD_API_BASE}/mp/tradinghours/markets/status?1=1"
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
