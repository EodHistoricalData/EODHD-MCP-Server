# app/tools/get_live_price_data.py

import logging
from collections.abc import Iterable, Sequence

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, sanitize_ticker
from app.response_formatter import ResourceResponse, format_json_response, format_text_response, raise_on_api_error

logger = logging.getLogger(__name__)

ALLOWED_FMT = {"json", "csv"}
MAX_EXTRA_TICKERS = 20  # soft limit recommended by docs (15–20)


def _normalize_symbols(symbols: Iterable[str] | None) -> list[str]:
    if not symbols:
        return []
    out: list[str] = []
    for s in symbols:
        if not s:
            continue
        s = str(s).strip()
        if s:
            out.append(sanitize_ticker(s, param_name="additional_symbols"))
    return out


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_live_price_data(
        ticker: str,
        additional_symbols: Sequence[str] | None = None,
        fmt: str = "json",
        api_token: str | None = None,
    ) -> ResourceResponse:
        """

        Get the current (delayed ~15-20 min) price snapshot for one or more tickers.
        Returns last trade price, change, change percent, volume, high, low, open, previous close, and timestamp.
        Supports stocks, ETFs, indices, forex, and crypto. Batch up to 20 symbols in one call.
        For US stocks with bid/ask, 52w range, and market cap, use get_us_live_extended_quotes instead.
        For historical daily/weekly/monthly OHLCV, use get_historical_stock_prices instead.

        Args:
            ticker (str): Primary symbol in SYMBOL.EXCHANGE format (e.g., 'AAPL.US').
                          Required and placed in the path, per API spec.
            additional_symbols (Sequence[str], optional): Extra symbols for 's=' query param,
                          comma-separated by the tool (e.g., ['VTI', 'EUR.FOREX']).
                          Docs recommend <= 15–20 total.
            fmt (str): 'json' or 'csv'. Defaults to 'json' for easier client handling.
            api_token (str, optional): Per-call token override. If omitted, env token is used.

        Returns:
            Single object (one ticker) or array (multiple tickers), each with:
            - code (str): ticker symbol
            - timestamp (int): Unix epoch seconds of last trade
            - open, high, low, close (float): session OHLC
            - volume (int): session volume
            - previousClose (float): prior session close
            - change (float): absolute change from previousClose
            - change_p (float): percent change from previousClose

            Prices are delayed ~15-20 min depending on exchange.

        Examples:
            "Current Apple price" → ticker="AAPL.US"
            "Live quotes for Tesla, Google, and Amazon" → ticker="TSLA.US", additional_symbols=["GOOG.US", "AMZN.US"]
            "Bitcoin and Ethereum prices right now" → ticker="BTC-USD.CC", additional_symbols=["ETH-USD.CC"]


        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        # --- Validate inputs ---
        ticker = sanitize_ticker(ticker)

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        extras = _normalize_symbols(additional_symbols)
        # Prevent duplicates of the primary ticker in 's='
        extras = [s for s in extras if s != ticker]

        if len(extras) > MAX_EXTRA_TICKERS:
            raise ToolError(
                f"Too many symbols in 'additional_symbols'. Got {len(extras)}, max recommended is {MAX_EXTRA_TICKERS}."
            )

        # --- Build URL per docs ---
        # Example: /api/real-time/AAPL.US?fmt=json&s=VTI,EUR.FOREX
        url = build_url(
            f"real-time/{ticker}",
            {
                "fmt": fmt,
                "s": ",".join(extras) if extras else None,
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
            return format_text_response(data, "text/csv", resource_path=f"real-time/{ticker}.csv")

        return format_json_response(data)
