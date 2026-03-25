# app/tools/get_historical_stock_prices.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, coerce_date_param, sanitize_ticker, validate_date_range
from app.response_formatter import ResourceResponse, format_json_response, format_text_response, raise_on_api_error

logger = logging.getLogger(__name__)

ALLOWED_PERIODS = {"d", "w", "m"}  # daily, weekly, monthly (per docs)
ALLOWED_ORDER = {"a", "d"}  # ascending, descending (per docs)
ALLOWED_FMT = {"json", "csv"}  # default is csv in API, but we default to json here


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_historical_stock_prices(
        ticker: str,
        start_date: str | None = None,
        end_date: str | None = None,
        period: str = "d",
        order: str = "a",
        fmt: str = "json",
        filter: str | None = None,  # e.g., "last_close", "last_volume"
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Get historical daily, weekly, or monthly OHLCV price data for any stock, ETF, index, or crypto.
        Covers open, high, low, close, adjusted close, and volume for a date range.
        Use for price history, charting, backtesting, and performance analysis.
        For intraday candles (1min-1h), use get_intraday_historical_data instead.
        For current/live prices, use get_live_price_data instead.

        Args:
            ticker (str): Symbol in SYMBOL.EXCHANGE format, e.g. 'AAPL.US'.
            start_date (str, optional): 'from' date in YYYY-MM-DD. If omitted, API returns full history (plan limits apply).
            end_date (str, optional): 'to' date in YYYY-MM-DD. If omitted, API returns up to most recent.
            period (str): 'd' (daily), 'w' (weekly), 'm' (monthly). Default 'd'.
            order (str): 'a' (ascending) or 'd' (descending). Default 'a'.
            fmt (str): 'json' or 'csv'. Default 'json'. (API default is csv.)
            filter (str, optional): e.g., 'last_close', 'last_volume' (works with fmt=json; returns a single value).
            api_token (str, optional): Override API token for this call. If not provided, env token is used.

        Returns:
            Array of daily/weekly/monthly records, each with:
            - date (str): YYYY-MM-DD
            - open, high, low, close (float): OHLC prices (unadjusted)
            - adjusted_close (float): split- and dividend-adjusted close
            - volume (int): shares traded

            Use adjusted_close for return calculations; close is raw exchange price.
            If filter is set (e.g. 'last_close'), returns a single scalar value.

        Examples:
            "Apple stock price last month" → ticker="AAPL.US", start_date="2026-02-01", end_date="2026-02-28"
            "Weekly Tesla for 2025" → ticker="TSLA.US", period="w", start_date="2025-01-01", end_date="2025-12-31"
            "Monthly S&P 500 since 2020" → ticker="GSPC.INDX", period="m", start_date="2020-01-01"

        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        # --- Validate required/typed params ---
        ticker = sanitize_ticker(ticker)

        if period not in ALLOWED_PERIODS:
            raise ToolError(f"Invalid 'period'. Allowed values: {sorted(ALLOWED_PERIODS)}")

        if order not in ALLOWED_ORDER:
            raise ToolError(f"Invalid 'order'. Allowed values: {sorted(ALLOWED_ORDER)}")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed values: {sorted(ALLOWED_FMT)}")

        start_date = coerce_date_param(start_date, "start_date")
        end_date = coerce_date_param(end_date, "end_date")
        validate_date_range(start_date, end_date)

        url = build_url(
            f"eod/{ticker}",
            {
                "period": period,
                "order": order,
                "fmt": fmt,
                "from": start_date,
                "to": end_date,
                "filter": filter,
                "api_token": api_token,
            },
        )

        # --- Execute request ---
        data = await make_request(url, response_mode="text" if fmt == "csv" else "json")
        raise_on_api_error(data)

        if fmt == "csv":
            if not isinstance(data, str):
                raise ToolError("Unexpected CSV response format from API.")
            return format_text_response(data, "text/csv", resource_path=f"eod/{ticker}.csv")

        return format_json_response(data)
