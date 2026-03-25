# app/tools/get_upcoming_ipos.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, coerce_date_param, validate_date_range
from app.response_formatter import ResourceResponse, format_json_response, format_text_response, raise_on_api_error

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_upcoming_ipos(
        from_date: str | None = None,  # format YYYY-MM-DD (mapped to 'from')
        to_date: str | None = None,  # format YYYY-MM-DD (mapped to 'to')
        fmt: str = "json",  # 'json' or 'csv' (default per API is csv; we default to json for dev-friendliness)
        api_token: str | None = None,  # per-call override; otherwise env EODHD_API_KEY is used
    ) -> ResourceResponse:
        """

        Get upcoming and recent IPO (Initial Public Offering) listings.
        Returns IPO dates, company names, exchanges, share prices, and deal details within a date range (defaults to next 7 days).
        Use when the user asks about new stock listings, companies going public, or IPO calendar.
        For stock splits calendar, use get_upcoming_splits. For dividend calendar, use get_upcoming_dividends.


        Returns:
            Object with:
            - ipos (list): array of IPO records, each with:
              - code (str): ticker symbol
              - name (str): company name
              - exchange (str): exchange code
              - currency (str): pricing currency
              - start_date (str): expected IPO date
              - filing_date (str): SEC filing date
              - amended_date (str): last amendment date
              - price_from (float|null): low end of price range
              - price_to (float|null): high end of price range
              - offer_price (float|null): final offer price
              - shares (int|null): shares offered
              - deal_type (str): type of offering (e.g. 'Priced')

        Examples:
            "IPOs this week" → from_date="2026-03-02", to_date="2026-03-06"
            "IPOs in March 2026" → from_date="2026-03-01", to_date="2026-03-31"
            "Upcoming IPOs next 30 days" → from_date="2026-03-06", to_date="2026-04-05"


        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        # Normalize/validate fmt
        fmt = (fmt or "json").lower()
        if fmt not in ("json", "csv"):
            raise ToolError("Invalid 'fmt'. Allowed values: 'json', 'csv'.")

        # --- Coerce dates ---
        from_date = coerce_date_param(from_date, "from_date")
        to_date = coerce_date_param(to_date, "to_date")
        validate_date_range(from_date, to_date, "from_date", "to_date")

        # Build URL
        url = build_url(
            "calendar/ipos",
            {
                "from": from_date,
                "to": to_date,
                "fmt": fmt,
                "api_token": api_token,
            },
        )

        # Call
        data = await make_request(url, response_mode="text" if fmt == "csv" else "json")
        raise_on_api_error(data)

        # Handle response

        if fmt == "csv":
            if not isinstance(data, str):
                raise ToolError("Unexpected CSV response format from API.")
            return format_text_response(data, "text/csv", resource_path="calendar/ipos.csv")

        return format_json_response(data)
