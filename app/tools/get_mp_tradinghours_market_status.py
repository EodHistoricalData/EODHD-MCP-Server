# app/tools/get_mp_tradinghours_market_status.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_tradinghours_market_status(
        fin_id: str,  # e.g. "us.nyse"
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
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

        url = build_url(
            "mp/tradinghours/markets/status",
            {
                "fin_id": fin_id.strip(),
                "api_token": api_token,
            },
        )

        data = await make_request(url)

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
