# app/tools/get_symbol_change_history.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, coerce_date_param, validate_date_range
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_symbol_change_history(
        start_date: str | None = None,  # maps to 'from' (YYYY-MM-DD)
        end_date: str | None = None,  # maps to 'to'   (YYYY-MM-DD)
        fmt: str = "json",  # API returns json here; we gate to json
        api_token: str | None = None,  # per-call token override
    ) -> ResourceResponse:
        """

        Get ticker symbol change history -- tracks when US stocks changed their ticker symbol or company name.
        Returns old symbol, new symbol, company name, exchange, and effective date. Data available from 2022-07-22, US exchanges only.
        Use when the user asks about ticker renames, symbol changes, rebranding events, or needs to map old tickers to new ones.
        This is the only tool for symbol/ticker change tracking.

        Args:
            start_date (str, optional): 'from' in YYYY-MM-DD (e.g., '2022-10-01').
            end_date (str, optional):   'to' in YYYY-MM-DD   (e.g., '2022-11-01').
            fmt (str): 'json' (default).
            api_token (str, optional): Per-call token override; env token used if omitted.

        Returns:
            Array of symbol change records, each with:
            - old_code (str): previous ticker symbol
            - old_exchange (str): previous exchange code
            - old_country (str): previous country code
            - new_code (str): new ticker symbol
            - new_exchange (str): new exchange code
            - new_country (str): new country code
            - date (str): effective date of change

        Examples:
            "Symbol changes this month" → start_date="2026-03-01", end_date="2026-03-06"
            "Ticker renames in 2025" → start_date="2025-01-01", end_date="2025-12-31"
            "Recent symbol changes last 90 days" → start_date="2025-12-06", end_date="2026-03-06"

        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        # Validate inputs
        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        start_date = coerce_date_param(start_date, "start_date")
        end_date = coerce_date_param(end_date, "end_date")
        validate_date_range(start_date, end_date)

        # Build URL
        # Example:
        # /api/symbol-change-history?from=2022-10-01&to=2022-11-01&fmt=json
        url = build_url(
            "symbol-change-history",
            {
                "fmt": fmt,
                "from": start_date,
                "to": end_date,
                "api_token": api_token,
            },
        )

        # Request
        data = await make_request(url)

        # Normalize / return

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
