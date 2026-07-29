# app/tools/get_congressional_trades.py


import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_query_param, build_url
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)

_CHAMBERS = ("senate", "house")
_TRANSACTION_TYPES = ("purchase", "sale", "exchange")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Congressional Trades", readOnlyHint=True))
    async def get_congressional_trades(
        symbol: str | None = None,  # ticker filter, e.g. AAPL
        chamber: str | None = None,  # senate | house
        bioguide_id: str | None = None,  # member id, e.g. S000250
        transaction_type: str | None = None,  # purchase,sale,exchange (comma-separated)
        transaction_date_from: str | None = None,  # YYYY-MM-DD
        transaction_date_to: str | None = None,  # YYYY-MM-DD
        disclosure_date_from: str | None = None,  # YYYY-MM-DD
        disclosure_date_to: str | None = None,  # YYYY-MM-DD
        limit: int | str | None = None,  # page[limit]
        offset: int | str | None = None,  # page[offset]
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch US Congress stock-trade disclosures filed under the STOCK Act. Use when the user asks
        about congressional trading, which stocks a senator or representative bought or sold, politician
        trades, or Senate/House financial disclosures.

        Covers both chambers in one feed, sourced from the official Senate EFD and House Clerk portals.
        Filter by ticker, chamber, member (Bioguide ID), transaction type, and transaction or disclosure
        date range. Requires the All-in-One plan. Costs 10 API calls per request.

        Args:
            symbol (str, optional): Ticker symbol, e.g. "AAPL".
            chamber (str, optional): "senate" or "house".
            bioguide_id (str, optional): Member Bioguide ID, e.g. "S000250".
            transaction_type (str, optional): One or more of "purchase", "sale", "exchange"
                (comma-separated for multiple).
            transaction_date_from (str, optional): Earliest transaction date, YYYY-MM-DD.
            transaction_date_to (str, optional): Latest transaction date, YYYY-MM-DD.
            disclosure_date_from (str, optional): Earliest disclosure date, YYYY-MM-DD.
            disclosure_date_to (str, optional): Latest disclosure date, YYYY-MM-DD.
            limit (int, optional): Records per page (default 20, max 100).
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override.

        Returns:
            Envelope with data, meta (total, page), and links (next). Each record has:
            - chamber (str): senate or house
            - member (obj): bioguide_id, first_name, last_name, full_name, office, state, party, district
            - asset (obj): symbol, description, asset_type
            - transaction (obj): type, transaction_date, disclosure_date, owner, amount_range,
              amount_low, amount_high, days_to_disclose, is_late, comment
            - source (obj): filing_url, source_system, filing_identifier

        Notes:
            - 10 API calls per request.
            - Requires the All-in-One plan.
            - Filters are flat query keys; only pagination uses page[limit] / page[offset].

        Examples:
            "Recent congressional trades" → get_congressional_trades()
            "Senate purchases and sales in 2026" → get_congressional_trades(chamber="senate", transaction_type="purchase,sale", transaction_date_from="2026-01-01")
            "Which trades did member S000250 make in Apple" → get_congressional_trades(bioguide_id="S000250", symbol="AAPL")
        """
        if chamber is not None:
            chamber = str(chamber).strip().lower()
            if chamber not in _CHAMBERS:
                raise ToolError("Parameter 'chamber' must be 'senate' or 'house'.")

        if transaction_type is not None:
            for value in str(transaction_type).split(","):
                if value.strip().lower() not in _TRANSACTION_TYPES:
                    raise ToolError(
                        "Parameter 'transaction_type' values must be one of 'purchase', 'sale', 'exchange'."
                    )

        lim: int | None = None
        if limit is not None:
            try:
                lim = int(limit)
            except (ValueError, TypeError):
                raise ToolError("Parameter 'limit' must be a positive integer.")
            if lim <= 0:
                raise ToolError("Parameter 'limit' must be a positive integer.")

        off: int | None = None
        if offset is not None:
            try:
                off = int(offset)
            except (ValueError, TypeError):
                raise ToolError("Parameter 'offset' must be a non-negative integer.")
            if off < 0:
                raise ToolError("Parameter 'offset' must be a non-negative integer.")

        url = build_url(
            "congressional-trades",
            {"api_token": api_token},
        )
        url += build_query_param("symbol", symbol)
        url += build_query_param("chamber", chamber)
        url += build_query_param("bioguide_id", bioguide_id)
        url += build_query_param("transaction_type", transaction_type)
        url += build_query_param("transaction_date_from", transaction_date_from)
        url += build_query_param("transaction_date_to", transaction_date_to)
        url += build_query_param("disclosure_date_from", disclosure_date_from)
        url += build_query_param("disclosure_date_to", disclosure_date_to)
        url += build_query_param("page[limit]", lim)
        url += build_query_param("page[offset]", off)

        data = await make_request(url)

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
