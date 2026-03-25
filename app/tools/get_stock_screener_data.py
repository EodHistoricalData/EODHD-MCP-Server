# app/tools/get_stock_screener_data.py

import json
import logging
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def _normalize_filters(filters: str | list[list[Any]] | None) -> str | None:
    """
    Accepts either:
      - a raw (already-encoded) string like:
        [[\"market_capitalization\",\">\",1000],[\"sector\",\"=\",\"Technology\"]]
      - a python list of lists like:
        [["market_capitalization", ">", 1000], ["sector", "=", "Technology"]]
    Returns a JSON string (not URL-encoded).
    """
    if filters is None or filters == "":
        return None
    if isinstance(filters, str):
        # Assume user passed a JSON-ish string already.
        return filters
    try:
        return json.dumps(filters, separators=(",", ":"))
    except Exception:
        logger.debug("Suppressed exception", exc_info=True)
        return None


def _normalize_signals(signals: str | list[str] | None) -> str | None:
    """
    Accepts either a comma-separated string or a list of strings.
    Returns a comma-separated string or None.
    """
    if signals is None or signals == "":
        return None
    if isinstance(signals, str):
        return signals
    # list
    parts = [s for s in signals if isinstance(s, str) and s.strip()]
    return ",".join(parts) if parts else None


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def stock_screener(
        filters: str | list[list[Any]] | None = None,
        signals: str | list[str] | None = None,
        sort: str | None = None,  # e.g. "market_capitalization.desc"
        limit: int = 50,  # 1..100
        offset: int = 0,  # 0..999
        fmt: str | None = None,  # NEW: accept fmt to avoid validation errors
        api_token: str | None = None,  # per-call override (else env)
    ) -> ResourceResponse:
        """

        Screen and filter stocks by fundamental and technical criteria.
        Build custom queries using filters (e.g., market_cap > 1B, sector = Technology, P/E < 20)
        and signals (e.g., 200d_new_hi, 50d_new_lo, bookvalue_neg, wallstreetbull).
        Returns matching tickers with key metrics. Supports sorting, pagination (limit up to 100).
        Consumes 5 API calls per request.
        Use this tool for stock discovery, screening by fundamentals/technicals, and building watchlists.
        For detailed data on a specific ticker, use get_fundamentals_data instead.

        Args:
          - filters: list-of-lists or JSON string
          - signals: list[str] or comma-separated string
          - sort: "field.asc" | "field.desc"
          - limit: 1..100
          - offset: 0..999
          - fmt: optional; Screener is JSON-only. If provided, must be "json".
          - api_token: optional override


        Returns:
            Array of matching stocks, each with:
            - code (str): ticker symbol
            - name (str): company name
            - exchange (str): exchange code (e.g. 'US')
            - sector (str): GICS sector
            - industry (str): GICS industry
            - market_capitalization (float): market cap in USD
            Plus any fields relevant to applied filters/signals, e.g.:
            - earnings_share, dividend_yield, price, change, volume, etc.

            Max 100 results per page; use offset for pagination.

        Examples:
            "Large-cap tech stocks" → filters=[["market_capitalization",">",10000000000],["sector","=","Technology"]], sort="market_capitalization.desc", limit=20
            "Stocks hitting new 52-week highs" → signals=["52weekhigh"], limit=50
            "Undervalued healthcare with high volume" → filters=[["sector","=","Healthcare"],["pe_ratio","<",15],["avgvol_200d",">",1000000]], sort="pe_ratio.asc"


        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """

        # --- fmt handling (for compatibility with callers passing fmt) ---
        if fmt is not None and fmt.lower() != "json":
            raise ToolError("The Screener endpoint returns JSON only. Use fmt='json' or omit this parameter.")

        # Validate pagination bounds
        if not (1 <= int(limit) <= 100):
            raise ToolError("Parameter 'limit' must be between 1 and 100.")
        if not (0 <= int(offset) <= 999):
            raise ToolError("Parameter 'offset' must be between 0 and 999.")

        filt_str = _normalize_filters(filters)
        if filters is not None and filt_str is None:
            raise ToolError("Invalid 'filters' value. Provide a JSON string or list-of-lists.")

        sig_str = _normalize_signals(signals)
        if signals is not None and (sig_str is None or sig_str.strip() == ""):
            raise ToolError("Invalid 'signals' value. Provide a list of strings or comma-separated string.")

        # Build URL
        # (We deliberately do NOT append fmt, since the endpoint is JSON-only.)
        url = build_url(
            "screener",
            {
                "sort": sort,
                "limit": str(limit),
                "offset": str(offset),
                "filters": filt_str,
                "signals": sig_str,
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
            raise ToolError("Unexpected JSON response format from API.") from e
