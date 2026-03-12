# get_mp_tradinghours_market_status.py

from urllib.parse import quote_plus

from app.api_client import make_request
from app.config import EODHD_API_BASE
from app.response import format_json_response
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def _q(key: str, val: str | int | None) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_tradinghours_market_status(
        fin_id: str,  # e.g. "us.nyse"
        api_token: str | None = None,  # per-call override
    ) -> list:
        """

        [TradingHours] Check whether a market is currently open or closed. Use when asked
        "is the NYSE open?", "when does Tokyo close?", or any real-time market status question.
        Returns status (Open/Closed), reason, time until next status change, and next bell time.
        Does not cover circuit breakers or individual stock trading halts.
        Find the FinID first via get_mp_tradinghours_list_markets or get_mp_tradinghours_lookup_markets.
        For static market metadata (timezone, MIC, holidays), use get_mp_tradinghours_market_details.
        Consumes 10 API calls per request.

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

        Examples:
            "is NYSE open right now" → fin_id="us.nyse"
            "check if London Stock Exchange is trading" → fin_id="gb.lse"
            "NASDAQ market status" → fin_id="us.nasdaq"


        """
        if not fin_id or not isinstance(fin_id, str):
            raise ToolError("Parameter 'fin_id' is required (e.g. 'us.nyse').")

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
            return format_json_response(data)
        except Exception:
            raise ToolError("Unexpected response format from API.")
