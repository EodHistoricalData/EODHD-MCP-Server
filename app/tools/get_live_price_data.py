#get_live_price_data.py

import json
from typing import Iterable, Optional, Sequence

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations

ALLOWED_FMT = {"json", "csv"}
MAX_EXTRA_TICKERS = 20  # soft limit recommended by docs (15–20)

def _normalize_symbols(symbols: Optional[Iterable[str]]) -> list[str]:
    if not symbols:
        return []
    out: list[str] = []
    for s in symbols:
        if not s:
            continue
        s = str(s).strip()
        if s:
            out.append(s)
    return out

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_live_price_data(
        ticker: str,
        additional_symbols: Optional[Sequence[str]] = None,
        fmt: str = "json",
        api_token: Optional[str] = None,
    ) -> str:
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

        
        """
        # --- Validate inputs ---
        if not ticker or not isinstance(ticker, str):
            raise ToolError("Parameter 'ticker' is required (e.g., 'AAPL.US').")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        extras = _normalize_symbols(additional_symbols)
        # Prevent duplicates of the primary ticker in 's='
        extras = [s for s in extras if s != ticker]

        if len(extras) > MAX_EXTRA_TICKERS:
            raise ToolError(
                f"Too many symbols in 'additional_symbols'. "
                f"Got {len(extras)}, max recommended is {MAX_EXTRA_TICKERS}."
            )

        # --- Build URL per docs ---
        # Example: /api/real-time/AAPL.US?fmt=json&s=VTI,EUR.FOREX
        url = f"{EODHD_API_BASE}/real-time/{ticker}?fmt={fmt}"
        if extras:
            url += f"&s={','.join(extras)}"

        # Per-call token override. If omitted, make_request will append env token.
        if api_token:
            url += f"&api_token={api_token}"

        # --- Request ---
        data = await make_request(url)

        # --- Normalize errors / outputs ---
        if data is None:
            raise ToolError("No response from API.")

        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        # If make_request always returns JSON (since it calls response.json()),
        # this will succeed for fmt=json. For fmt=csv, consider adapting make_request to return text.
        try:
            return json.dumps(data, indent=2)
        except Exception:
            if isinstance(data, str):  # if you adapted make_request to return text for CSV
                return json.dumps({"csv": data}, indent=2)
            raise ToolError("Unexpected response format from API.")
