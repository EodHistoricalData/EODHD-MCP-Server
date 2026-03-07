# get_upcoming_ipos.py

import json
from urllib.parse import quote_plus

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def _q(key: str, val: str | None) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_upcoming_ipos(
        from_date: str | None = None,  # format YYYY-MM-DD (mapped to 'from')
        to_date: str | None = None,  # format YYYY-MM-DD (mapped to 'to')
        fmt: str = "json",  # 'json' or 'csv' (default per API is csv; we default to json for dev-friendliness)
        api_token: str | None = None,  # per-call override; otherwise env EODHD_API_KEY is used
    ) -> str:
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

        
        """
        # Normalize/validate fmt
        fmt = (fmt or "json").lower()
        if fmt not in ("json", "csv"):
            raise ToolError("Invalid 'fmt'. Allowed values: 'json', 'csv'.")

        # Build URL
        url = f"{EODHD_API_BASE}/calendar/ipos?1=1"
        if from_date:
            url += _q("from", from_date)
        if to_date:
            url += _q("to", to_date)
        url += _q("fmt", fmt)

        if api_token:
            url += _q("api_token", api_token)  # otherwise appended by make_request via env

        # Call
        data = await make_request(url)

        # Handle response
        if data is None:
            raise ToolError("No response from API.")

        # If fmt=csv, many clients of make_request return raw text (str)
        if fmt == "csv":
            if isinstance(data, str):
                # Wrap CSV in a small envelope for consistency
                return json.dumps({"fmt": "csv", "data": data}, indent=2)
            # Unexpected structure
            raise ToolError("Unexpected CSV response format from API.")

        # fmt == json
        try:
            # data should be a dict/list already; ensure string output
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected JSON response format from API.")
