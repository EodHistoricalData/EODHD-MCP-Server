# app/tools/get_upcoming_dividends.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_query_param, build_url, coerce_date_param, sanitize_ticker, validate_date_range
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_upcoming_dividends(
        symbol: str | None = None,  # maps to filter[symbol]
        date_eq: str | None = None,  # maps to filter[date_eq], YYYY-MM-DD
        date_from: str | None = None,  # maps to filter[date_from], YYYY-MM-DD
        date_to: str | None = None,  # maps to filter[date_to],   YYYY-MM-DD
        page_limit: int | None = None,  # maps to page[limit], 1..1000, default 1000
        page_offset: int | None = None,  # maps to page[offset], >=0, default 0
        fmt: str = "json",  # API supports JSON only
        api_token: str | None = None,  # per-call override; else env EODHD_API_KEY
    ) -> ResourceResponse:
        """

        Get historical and upcoming dividend payments for stocks.
        Returns ex-dividend dates, payment dates, dividend amounts, and currency for a given symbol or date.
        Requires at least one of 'symbol' or 'date_eq'. Supports date range filtering and pagination.
        Use when the user asks about dividend dates, payout history, yield data, or ex-dividend calendars.
        For IPO calendar, use get_upcoming_ipos. For stock splits calendar, use get_upcoming_splits.


        Returns:
            Array of dividend records, each with:
            - code (str): ticker symbol
            - exchange (str): exchange code
            - date (str): ex-dividend date
            - declarationDate (str): declaration date
            - recordDate (str): record date
            - paymentDate (str): payment date
            - period (str): frequency (e.g. 'Quarterly', 'Annual')
            - value (float): adjusted dividend per share
            - unadjustedValue (float): unadjusted dividend per share
            - currency (str): dividend currency

        Examples:
            "Apple dividends in 2025" → symbol="AAPL.US", date_from="2025-01-01", date_to="2025-12-31"
            "All dividends on March 15" → date_eq="2026-03-15"
            "Microsoft dividends this quarter" → symbol="MSFT.US", date_from="2026-01-01", date_to="2026-03-31"


        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """

        # --- Validate basic args ---
        fmt = (fmt or "json").lower()
        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool (fmt must be 'json').")

        if symbol is None and date_eq is None:
            raise ToolError("You must provide at least one of 'symbol' or 'date_eq'.")

        if isinstance(symbol, str) and not symbol.strip():
            symbol = None
        elif symbol is not None:
            symbol = sanitize_ticker(symbol, param_name="symbol")

        if page_limit is not None:
            if not isinstance(page_limit, int) or not (1 <= page_limit <= 1000):
                raise ToolError("'page_limit' must be an integer between 1 and 1000.")

        if page_offset is not None:
            if not isinstance(page_offset, int) or page_offset < 0:
                raise ToolError("'page_offset' must be a non-negative integer.")

        # --- Coerce dates ---
        date_eq = coerce_date_param(date_eq, "date_eq")
        date_from = coerce_date_param(date_from, "date_from")
        date_to = coerce_date_param(date_to, "date_to")
        validate_date_range(date_from, date_to, "date_from", "date_to")

        # --- Build URL ---
        # Base: /api/calendar/dividends?filter[symbol]=...&filter[date_from]=...&page[limit]=...&page[offset]=...&fmt=json
        url = build_url(
            "calendar/dividends",
            {
                "fmt": fmt,
                "api_token": api_token,
            },
        )
        url += build_query_param("filter[symbol]", symbol)
        url += build_query_param("filter[date_eq]", date_eq)
        url += build_query_param("filter[date_from]", date_from)
        url += build_query_param("filter[date_to]", date_to)
        url += build_query_param("page[limit]", page_limit)
        url += build_query_param("page[offset]", page_offset)

        # --- Request upstream ---
        data = await make_request(url)

        # --- Return normalized JSON string ---
        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected JSON response format from API.") from e
