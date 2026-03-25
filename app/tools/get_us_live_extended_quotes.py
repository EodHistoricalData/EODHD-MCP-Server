# app/tools/get_us_live_extended_quotes.py

import logging
from collections.abc import Iterable, Sequence

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_query_param, build_url, sanitize_ticker
from app.response_formatter import ResourceResponse, format_json_response, format_text_response, raise_on_api_error

logger = logging.getLogger(__name__)

ALLOWED_FMT = {"json", "csv"}
MAX_PAGE_LIMIT = 100  # per spec
DEFAULT_FMT = "json"


def _normalize_symbols(symbols: str | Iterable[str] | None) -> list[str]:
    """
    Accepts a single comma-separated string or an iterable of strings.
    Strips whitespace, removes empties, preserves order, and de-duplicates.
    """
    out: list[str] = []
    seen = set()

    if symbols is None:
        return out

    # If passed a single string, support comma-separated list
    if isinstance(symbols, str):
        parts = [p.strip() for p in symbols.split(",")]
    else:
        parts = []
        for s in symbols:
            if s is None:
                continue
            parts.append(str(s).strip())

    for p in parts:
        if not p:
            continue
        p = sanitize_ticker(p, param_name="symbols")
        if p not in seen:
            out.append(p)
            seen.add(p)
    return out


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_us_live_extended_quotes(
        symbols: str | Sequence[str],  # one or more (e.g., "AAPL.US,TSLA.US" or ["AAPL.US","TSLA.US"])
        fmt: str = DEFAULT_FMT,  # 'json' (default) or 'csv'
        page_limit: int | None = None,  # page[limit] (max 100)
        page_offset: int | None = None,  # page[offset] (>= 0)
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Get extended delayed quotes for US stocks with rich detail beyond basic live prices.
        Returns last trade, bid/ask with sizes and event timestamps, rolling averages (50d/200d),
        52-week high/low, market cap, EPS, PE ratio, dividend yield, and more per symbol.
        Supports batching multiple US tickers in one call. 1 API call per ticker.
        For non-US tickers or basic global live prices, use get_live_price_data instead.
        For historical end-of-day data, use get_historical_stock_prices instead.

        Args:
          symbols: A single comma-separated string or a sequence of tickers (e.g., ["AAPL.US","TSLA.US"]).
          fmt: 'json' (default) or 'csv'.
          page_limit: Optional page size; max 100.
          page_offset: Optional offset for pagination; must be >= 0.
          api_token: Optional token; if omitted, env is used via make_request().

        Returns:
            Array of extended quote snapshots, each with:
            - code (str): ticker symbol
            - timestamp (int): Unix epoch seconds of last trade
            - open, high, low, close (float): session OHLC
            - volume (int): session volume
            - previousClose (float): prior session close
            - change (float): absolute change from previousClose
            - change_p (float): percent change
            - 50day_ma, 200day_ma (float): rolling moving averages
            - yearHigh, yearLow (float): 52-week high/low
            - marketCapitalization (float): market cap in USD
            - epsEstimateCurrentYear (float): consensus EPS estimate
            - eps (float): trailing EPS
            - pe (float): trailing P/E ratio
            - dividend_yield_percent (float): indicated annual dividend yield %
            - bid, ask (float): current bid/ask prices
            - bidSize, askSize (int): bid/ask lot sizes

            Prices are delayed ~15-20 min (exchange-compliant).

        Examples:
            "Extended quote for Apple" → symbols="AAPL.US"
            "Batch quotes for FAANG stocks" → symbols=["META.US", "AAPL.US", "AMZN.US", "NFLX.US", "GOOG.US"]
            "Tesla and Nvidia with pagination" → symbols=["TSLA.US", "NVDA.US"], page_limit=10, page_offset=0


        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        # --- Validate inputs ---
        syms = _normalize_symbols(symbols)
        if not syms:
            raise ToolError("Parameter 'symbols' must contain at least one ticker (e.g., 'AAPL.US').")

        fmt = (fmt or DEFAULT_FMT).lower()
        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        if page_limit is not None:
            if not isinstance(page_limit, int) or page_limit <= 0 or page_limit > MAX_PAGE_LIMIT:
                raise ToolError(f"'page_limit' must be an integer between 1 and {MAX_PAGE_LIMIT}.")

        if page_offset is not None:
            if not isinstance(page_offset, int) or page_offset < 0:
                raise ToolError("'page_offset' must be an integer >= 0.")

        # --- Build URL ---
        url = build_url(
            "us-quote-delayed",
            {
                "s": ",".join(syms),
                "fmt": fmt,
                "api_token": api_token,
            },
        )
        url += build_query_param("page[limit]", page_limit)
        url += build_query_param("page[offset]", page_offset)

        # --- Request ---
        data = await make_request(url, response_mode="text" if fmt == "csv" else "json")
        raise_on_api_error(data)

        # --- Normalize / return ---

        if fmt == "csv":
            if not isinstance(data, str):
                raise ToolError("Unexpected CSV response format from API.")
            return format_text_response(data, "text/csv", resource_path="us-quote-delayed/quotes.csv")

        return format_json_response(data)
