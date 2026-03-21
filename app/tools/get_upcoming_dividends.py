# get_upcoming_dividends.py

from app.api_client import make_request
from app.input_formatter import build_url
from app.response_formatter import format_json_response
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


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
    ) -> list:
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


        """

        # --- Validate basic args ---
        fmt = (fmt or "json").lower()
        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool (fmt must be 'json').")

        if symbol is None and date_eq is None:
            raise ToolError("You must provide at least one of 'symbol' or 'date_eq'.")

        if page_limit is not None:
            if not isinstance(page_limit, int) or not (1 <= page_limit <= 1000):
                raise ToolError("'page_limit' must be an integer between 1 and 1000.")

        if page_offset is not None:
            if not isinstance(page_offset, int) or page_offset < 0:
                raise ToolError("'page_offset' must be a non-negative integer.")

        # --- Build URL ---
        # Base: /api/calendar/dividends?filter[symbol]=...&filter[date_from]=...&page[limit]=...&page[offset]=...&fmt=json
        url = build_url(
            "calendar/dividends",
            {
                "fmt": fmt,
                "filter[symbol]": symbol,
                "filter[date_eq]": date_eq,
                "filter[date_from]": date_from,
                "filter[date_to]": date_to,
                "page[limit]": page_limit,
                "page[offset]": page_offset,
                "api_token": api_token,
            },
        )

        # --- Request upstream ---
        data = await make_request(url)

        # --- Return normalized JSON string ---
        try:
            return format_json_response(data)
        except Exception:
            raise ToolError("Unexpected JSON response format from API.")
