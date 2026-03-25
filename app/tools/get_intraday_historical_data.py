# app/tools/get_intraday_historical_data.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, coerce_timestamp_param, sanitize_ticker, validate_timestamp_range
from app.response_formatter import ResourceResponse, format_json_response, format_text_response, raise_on_api_error

logger = logging.getLogger(__name__)

ALLOWED_INTERVALS = {"1m", "5m", "1h"}  # per docs
ALLOWED_FMT = {"json", "csv"}

# Max allowed "from->to" span per docs (in days)
MAX_RANGE_DAYS = {
    "1m": 120,
    "5m": 600,
    "1h": 7200,
}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_intraday_historical_data(
        ticker: str,
        interval: str = "5m",
        # Now accept unix seconds or date strings for both:
        from_timestamp: int | str | None = None,
        to_timestamp: int | str | None = None,
        fmt: str = "json",
        split_dt: bool | None = False,
        api_token: str | None = None,
    ) -> ResourceResponse:
        """

        Get historical intraday OHLCV candles at 1-minute, 5-minute, or 1-hour intervals.
        Use for intraday price analysis, short-term patterns, and high-resolution charting.
        Accepts date strings or Unix timestamps for the time range.
        Max range depends on interval: 1m=120 days, 5m=600 days, 1h=7200 days.
        For daily/weekly/monthly end-of-day bars, use get_historical_stock_prices instead.
        For current live price, use get_live_price_data instead.

        Args:
            ticker (str): SYMBOL.EXCHANGE_ID, e.g. 'AAPL.US'.
            interval (str): One of {'1m','5m','1h'}. Default '5m'.
            from_timestamp (int|str, optional): Start as Unix seconds OR a date string
                (auto-detected). Examples: 1704067200, '2024-01-01', '01-01-24', '01/01/2024',
                '2024-01-01T15:30:00Z', 'Jan 1, 2024'.
            to_timestamp (int|str, optional): End as Unix seconds OR a date string (auto-detected).
            fmt (str): 'json' or 'csv'. Default 'json'.
            split_dt (bool, optional): If True, adds 'split-dt=1' to split date/time fields.
            api_token (str, optional): Per-call token override; env token used if omitted.

        Returns:
            Array of intraday bar records, each with:
            - timestamp (int): Unix epoch seconds
            - gmtoffset (int): GMT offset in seconds for the exchange
            - datetime (str): human-readable datetime (YYYY-MM-DD HH:MM:SS)
            - open, high, low, close (float): bar OHLC
            - volume (int): shares traded in this bar

        Notes:
            - If no 'from'/'to' provided, API returns last 120 days by default (per docs).
            - Max span depends on interval:
                1m -> 120 days, 5m -> 600 days, 1h -> 7200 days.

        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """

        # --- Validate required/typed params ---
        ticker = sanitize_ticker(ticker)

        if interval not in ALLOWED_INTERVALS:
            raise ToolError(f"Invalid 'interval'. Allowed: {sorted(ALLOWED_INTERVALS)}")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        # --- Coerce 'from'/'to' into Unix seconds (auto-detect strings, ms, etc.) ---
        from_ts = coerce_timestamp_param(from_timestamp, "from_timestamp")
        to_ts = coerce_timestamp_param(to_timestamp, "to_timestamp")
        validate_timestamp_range(from_ts, to_ts)

        # --- Enforce documented maximum range ---
        if from_ts is not None and to_ts is not None:
            span_seconds = to_ts - from_ts
            max_days = MAX_RANGE_DAYS[interval]
            if span_seconds > max_days * 86400:
                raise ToolError(f"Requested range exceeds maximum for interval '{interval}'. Max is {max_days} days.")

        # --- Build URL ---
        # Base: /api/intraday/{ticker}?fmt=...&interval=...&from=...&to=...&split-dt=1
        url = build_url(
            f"intraday/{ticker}",
            {
                "fmt": fmt,
                "interval": interval,
                "from": from_ts,
                "to": to_ts,
                "split-dt": 1 if split_dt else None,
                "api_token": api_token,
            },
        )

        # --- Request ---
        data = await make_request(url, response_mode="text" if fmt == "csv" else "json")
        raise_on_api_error(data)

        # --- Normalize errors / outputs ---

        if fmt == "csv":
            if not isinstance(data, str):
                raise ToolError("Unexpected CSV response format from API.")
            return format_text_response(data, "text/csv", resource_path=f"intraday/{ticker}-{interval}.csv")

        return format_json_response(data)
