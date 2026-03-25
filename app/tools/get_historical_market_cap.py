# app/tools/get_historical_market_cap.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, coerce_date_param, sanitize_ticker, validate_date_range
from app.response_formatter import ResourceResponse, format_json_response, format_text_response, raise_on_api_error

logger = logging.getLogger(__name__)

ALLOWED_FMT = {"json", "csv"}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_historical_market_cap(
        ticker: str,  # e.g., "AAPL" or "AAPL.US"
        start_date: str | None = None,  # maps to 'from' (YYYY-MM-DD)
        end_date: str | None = None,  # maps to 'to'   (YYYY-MM-DD)
        fmt: str = "json",  # 'json' or 'csv' (API shows json; csv optional)
        api_token: str | None = None,  # per-call override; env token otherwise
    ) -> ResourceResponse:
        """

        Get historical market capitalization data for a US stock over time.
        Returns weekly market cap data points (from 2020 onward) for NYSE/NASDAQ tickers.
        Filter by date range. Each request consumes 10 API calls.
        Use when the user asks about market cap history, company valuation over time, or market cap trends.
        This is the only tool for historical market cap -- do not confuse with fundamental data or price history.

        Returns:
            Array of weekly data points, each with:
            - date (str): observation date YYYY-MM-DD
            - value (float): market capitalization in USD

        Examples:
            "Apple market cap history in 2025" → ticker="AAPL.US", start_date="2025-01-01", end_date="2025-12-31"
            "Microsoft market cap last 6 months" → ticker="MSFT.US", start_date="2025-09-06", end_date="2026-03-06"
            "Google market cap since 2023" → ticker="GOOG.US", start_date="2023-01-01"

        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        # --- Validate inputs ---
        ticker = sanitize_ticker(ticker)

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        start_date = coerce_date_param(start_date, "start_date")
        end_date = coerce_date_param(end_date, "end_date")
        validate_date_range(start_date, end_date)

        # --- Build URL ---
        # Example: /api/historical-market-cap/AAPL.US?fmt=json&from=2025-03-01&to=2025-04-01
        url = build_url(
            f"historical-market-cap/{ticker}",
            {
                "fmt": fmt,
                "from": start_date,
                "to": end_date,
                "api_token": api_token,
            },
        )

        # --- Request ---
        data = await make_request(url, response_mode="text" if fmt == "csv" else "json")
        raise_on_api_error(data)

        # --- Normalize / return ---

        if fmt == "csv":
            if not isinstance(data, str):
                raise ToolError("Unexpected CSV response format from API.")
            return format_text_response(data, "text/csv", resource_path=f"historical-market-cap/{ticker}.csv")

        return format_json_response(data)
