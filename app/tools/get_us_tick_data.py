# get_us_tick_data.py

from app.api_client import make_request
from app.config import EODHD_API_BASE
from app.response_formatter import ResourceResponse, format_json_response, format_text_response
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

ALLOWED_FMT = {"json", "csv"}


def _to_int(name: str, v: int | str | None) -> int | None:
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.isdigit():
        return int(v)
    raise ValueError(f"'{name}' must be an integer UNIX timestamp in seconds (UTC).")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_us_tick_data(
        ticker: str,  # maps to s=
        from_timestamp: int | str,  # UNIX seconds (UTC)
        to_timestamp: int | str,  # UNIX seconds (UTC)
        limit: int = 1000,  # max number of ticks returned
        fmt: str = "json",  # 'json' | 'csv'
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch historical tick-level trade data for US equities. Use when the user needs
        individual trade records with exact timestamps, prices, volumes, and market venue
        identifiers at the finest granularity available.

        Returns individual trades (ticks) across all US venues for a given time range.
        Fields include timestamp (ms), price, shares, market, sub-market, sequence number.
        US stocks only. Costs 10 API calls per request.

        For real-time streaming ticks, use capture_realtime_ws instead.
        For daily/intraday OHLCV bars, use get_intraday_historical_data.

        Args:
            ticker (str): US ticker, e.g., 'AAPL' or 'AAPL.US'.
            from_timestamp (int|str): Start UNIX time in seconds (UTC).
            to_timestamp (int|str): End UNIX time in seconds (UTC).
            limit (int): Max ticks to return (default 1000).
            fmt (str): 'json' (default) or 'csv'.
            api_token (str, optional): Per-call token override.


        Returns:
            Array of tick objects, each with:
            - timestamp (int): UNIX timestamp in milliseconds
            - datetime (str): human-readable datetime
            - volume (int): tick volume (shares)
            - price (float): trade price
            - type (str): tick type (trade/quote)
            - conditions (str): trade condition codes

        Examples:
            "AAPL tick data on 2026-03-05 first 100 ticks" → get_us_tick_data(ticker="AAPL", from_timestamp=1772870400, to_timestamp=1772956800, limit=100)
            "TSLA trades between two timestamps" → get_us_tick_data(ticker="TSLA", from_timestamp=1772870400, to_timestamp=1772874000, limit=500)


        Demo:
            To test data structure, use the test API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        # --- Validate inputs ---
        if not ticker or not isinstance(ticker, str):
            raise ToolError("Parameter 'ticker' is required (e.g., 'AAPL' or 'AAPL.US').")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        try:
            f_ts = _to_int("from_timestamp", from_timestamp)
            t_ts = _to_int("to_timestamp", to_timestamp)
        except ValueError as ve:
            raise ToolError(str(ve))

        if f_ts is None or t_ts is None:
            raise ToolError("'from_timestamp' and 'to_timestamp' are required (UNIX seconds).")
        if f_ts < 0 or t_ts < 0:
            raise ToolError("Timestamps must be non-negative UNIX seconds.")
        if f_ts > t_ts:
            raise ToolError("'from_timestamp' cannot be greater than 'to_timestamp'.")

        if not isinstance(limit, int) or limit <= 0:
            raise ToolError("'limit' must be a positive integer.")

        # --- Build URL per docs ---
        # Example:
        # /api/ticks/?s=AAPL&from=1694455200&to=1694541600&limit=5&fmt=json
        url = f"{EODHD_API_BASE}/ticks/?s={ticker}&from={f_ts}&to={t_ts}&limit={limit}&fmt={fmt}"
        if api_token:
            url += f"&api_token={api_token}"  # otherwise make_request appends env token

        # --- Request ---
        data = await make_request(url, response_mode="text" if fmt == "csv" else "json")

        # --- Normalize / return ---
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        if fmt == "csv":
            if not isinstance(data, str):
                raise ToolError("Unexpected CSV response format from API.")
            return format_text_response(data, "text/csv", resource_path=f"ticks/{ticker}.csv")

        return format_json_response(data)
