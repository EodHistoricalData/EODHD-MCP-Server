# app/tools/get_realtime_minute_bars.py

import logging
from urllib.parse import urlencode

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import sanitize_ticker
from app.response_formatter import ResourceResponse, format_json_response, raise_on_api_error

logger = logging.getLogger(__name__)

# The real-time service answers on its own host, not on EODHD_API_BASE.
REALTIME_HOST = "https://ws.eodhistoricaldata.com"

# Only the Cboe equity markets keep bars. crypto and forex have none and answer with an
# empty array, which the tool reports as such rather than treating as an error.
VALID_MARKETS = ("us", "eu")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Real-Time Minute Bars", readOnlyHint=True))
    async def get_realtime_minute_bars(
        market: str,
        symbol: str,
        api_token: str | None = None,
    ) -> ResourceResponse:
        """
        Get the recent CLOSED one-minute OHLCV bars held by the real-time service for one symbol.

        Use when a stream was interrupted and the gap needs filling, or when a short window of
        recent minute bars is wanted without opening a WebSocket. For a live stream use
        capture_realtime_ws; for a single delayed snapshot use get_live_price_data; for deep
        intraday history use get_intraday_historical_data.

        Only minutes in which the symbol actually traded produce a bar, so the result is sparse
        rather than one bar per consecutive minute — a quiet name can return a handful of bars
        spanning several hours.

        Args:
            market (str): 'us' or 'eu'. These are the only markets that keep bars.
            symbol (str): US equities use plain tickers ('AAPL'); European equities use
                TICKER.EXCHANGE ('GSK.LSE'). The native Cboe symbol and the un-hyphenated
                alias of a dual-class ticker ('ERICB.ST' for 'ERIC-B.ST') are both accepted,
                and the reply always reports the canonical EODHD ticker in 's'.
            api_token (str, optional): Per-call token override. If omitted, env token is used.

        Returns:
            Array of bars, oldest first, each with:
            - s (str): canonical EODHD ticker, regardless of the form requested
            - i (str): bar interval, '1m'
            - t (int): bar OPEN time, epoch ms UTC
            - o, h, l, c (float): open, high, low, close
            - v (int): volume in shares accumulated within the bar

            An unknown symbol returns an empty array rather than an error.
        """
        market_clean = (market or "").strip().lower()
        if market_clean not in VALID_MARKETS:
            raise ToolError(
                f"Parameter 'market' must be one of {VALID_MARKETS}. Got: {market!r}. "
                "Only the Cboe equity markets keep minute bars; crypto and forex have none."
            )

        symbol_clean = sanitize_ticker(symbol, param_name="symbol")

        query = urlencode({"market": market_clean, "symbol": symbol_clean})
        url = f"{REALTIME_HOST}/history?{query}"

        logger.info("get_realtime_minute_bars market=%s symbol=%s", market_clean, symbol_clean)

        data = await make_request(url, response_mode="json")
        raise_on_api_error(data)
        return format_json_response(data, resource_path=f"realtime-minute-bars/{market_clean}/{symbol_clean}")
