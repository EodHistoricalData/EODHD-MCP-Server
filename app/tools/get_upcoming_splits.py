# app/tools/get_upcoming_splits.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, coerce_date_param, validate_date_range
from app.response_formatter import ResourceResponse, format_json_response, format_text_response, raise_on_api_error

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_upcoming_splits(
        from_date: str | None = None,  # YYYY-MM-DD → maps to 'from'
        to_date: str | None = None,  # YYYY-MM-DD → maps to 'to'
        fmt: str = "json",  # 'json' or 'csv' (API default is csv)
        api_token: str | None = None,  # per-call override; else env EODHD_API_KEY
    ) -> ResourceResponse:
        """

        Get upcoming and recent stock split events.
        Returns split dates, tickers, and split ratios (e.g., 4:1) within a date range (defaults to next 7 days).
        Use when the user asks about stock splits, share splits, or reverse splits.
        For IPO calendar, use get_upcoming_ipos. For dividend calendar, use get_upcoming_dividends.


        Returns:
            Array of split records, each with:
            - code (str): ticker symbol
            - exchange (str): exchange code
            - optionable (str): whether options exist ('0' or '1')
            - date (str): split effective date
            - split (str): split ratio (e.g. '4/1')
            - oldShares (int): pre-split share count
            - newShares (int): post-split share count

        Examples:
            "Stock splits this week" → from_date="2026-03-02", to_date="2026-03-06"
            "Splits in Q1 2026" → from_date="2026-01-01", to_date="2026-03-31"
            "Any splits next month" → from_date="2026-04-01", to_date="2026-04-30"


        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        fmt = (fmt or "json").lower()
        if fmt not in ("json", "csv"):
            raise ToolError("Invalid 'fmt'. Allowed values: 'json', 'csv'.")

        # --- Coerce dates ---
        from_date = coerce_date_param(from_date, "from_date")
        to_date = coerce_date_param(to_date, "to_date")
        validate_date_range(from_date, to_date, "from_date", "to_date")

        # Build URL
        url = build_url(
            "calendar/splits",
            {
                "from": from_date,
                "to": to_date,
                "fmt": fmt,
                "api_token": api_token,
            },
        )

        # Call upstream
        data = await make_request(url, response_mode="text" if fmt == "csv" else "json")
        raise_on_api_error(data)

        if fmt == "csv":
            if not isinstance(data, str):
                raise ToolError("Unexpected CSV response format from API.")
            return format_text_response(data, "text/csv", resource_path="calendar/splits.csv")

        return format_json_response(data)
