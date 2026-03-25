# app/tools/get_mp_tick_data.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, coerce_timestamp_param, sanitize_ticker, validate_timestamp_range
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_tick_data(
        ticker: str,  # maps to s=, e.g. "AAPL"
        from_timestamp: int | str | None = None,  # UNIX seconds (UTC)
        to_timestamp: int | str | None = None,  # UNIX seconds (UTC)
        limit: int | str | None = None,  # 1-10000
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        [Marketplace] Fetch individual trade ticks (tick-by-tick data) for US stocks. Use when
        asked about granular trade-level data, tick history, or microstructure analysis.
        Returns timestamp (ms), price, shares, market center, and sequence for each trade.
        Covers US equities only. Time range defaults to yesterday if not specified.
        This is the paid Marketplace tick data provider. For free-tier tick data, use get_us_tick_data.
        Consumes 10 API calls per request.

        Args:
            ticker (str): Ticker symbol, max 30 chars (e.g. 'AAPL', 'MSFT').
            from_timestamp (int, optional): Start UNIX time in seconds. Default: yesterday start.
            to_timestamp (int, optional): End UNIX time in seconds. Default: yesterday end.
            limit (int, optional): Max ticks to return (1-10000). Default: all in range.
            api_token (str, optional): Per-call token override; env token used otherwise.


        Returns:
            JSON array of tick objects, each with:
            - timestamp (int): Trade timestamp in UNIX seconds.
            - datetime (str): Human-readable UTC datetime.
            - gmtoffset (int): GMT offset in seconds.
            - type (str): Tick type identifier.
            - price (float): Trade price.
            - volume (int): Number of shares traded.
            - conditions (str): Trade condition codes.

        Notes:
            - Marketplace product: 10 API calls per request.
            - Timestamp params in seconds but response timestamps may differ in precision.
            - US stocks only.

        Examples:
            "AAPL tick data for yesterday" → ticker="AAPL"
            "first 500 TSLA ticks from March 3 2026" → ticker="TSLA", from_timestamp=1741003200, to_timestamp=1741089600, limit=500
            "MSFT trade ticks, max 1000" → ticker="MSFT", limit=1000


        """
        ticker = sanitize_ticker(ticker)

        if len(ticker) > 30:
            raise ToolError("Parameter 'ticker' must be at most 30 characters.")

        from_ts = coerce_timestamp_param(from_timestamp, "from_timestamp")
        to_ts = coerce_timestamp_param(to_timestamp, "to_timestamp")
        validate_timestamp_range(from_ts, to_ts)

        if limit is not None:
            try:
                lim = int(limit)
            except (ValueError, TypeError):
                raise ToolError("Parameter 'limit' must be an integer (1-10000).")
            if lim < 1 or lim > 10000:
                raise ToolError("Parameter 'limit' must be between 1 and 10000.")
        else:
            lim = None

        url = build_url(
            "mp/unicornbay/tickdata/ticks",
            {
                "s": ticker,
                "from": from_ts,
                "to": to_ts,
                "limit": lim,
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
