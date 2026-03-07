#get_ust_bill_rates.py

import json
from typing import Optional, Union

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_ust_bill_rates(
        year: Optional[Union[int, str]] = None,   # filter[year], e.g. 2024
        limit: Optional[Union[int, str]] = None,   # page[limit]
        offset: Optional[Union[int, str]] = None,  # page[offset]
        api_token: Optional[str] = None,            # per-call override
    ) -> str:
        """

        Fetch daily US Treasury Bill rates (discount and coupon-equivalent yields). Use when the
        user asks about T-bill rates, short-term government borrowing costs, or discount rates
        for Treasury bills.

        Returns daily rates for tenors: 4WK, 8WK, 13WK, 17WK, 26WK, 52WK. Fields include
        date, tenor, discount rate, coupon-equivalent yield, averages, maturity date, and CUSIP.
        Filterable by year. Costs 1 API call per request.

        For Treasury par yield curve rates (longer maturities up to 30Y), use get_ust_yield_rates.

        Args:
            year (int, optional): Filter by year (1900+). Defaults to current year.
            limit (int, optional): Records per page.
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override.


        Returns:
            Array of daily bill rate objects, each with:
            - date (str): observation date (YYYY-MM-DD)
            - 4WEEKS_BANK_DISCOUNT (float): 4-week bank discount rate
            - 4WEEKS_COUPON_EQUIVALENT (float): 4-week coupon equivalent yield
            - 8WEEKS_BANK_DISCOUNT (float): 8-week bank discount rate
            - 8WEEKS_COUPON_EQUIVALENT (float): 8-week coupon equivalent yield
            - 13WEEKS_BANK_DISCOUNT (float): 13-week bank discount rate
            - 13WEEKS_COUPON_EQUIVALENT (float): 13-week coupon equivalent yield
            - 17WEEKS_BANK_DISCOUNT (float): 17-week bank discount rate
            - 17WEEKS_COUPON_EQUIVALENT (float): 17-week coupon equivalent yield
            - 26WEEKS_BANK_DISCOUNT (float): 26-week bank discount rate
            - 26WEEKS_COUPON_EQUIVALENT (float): 26-week coupon equivalent yield
            - 52WEEKS_BANK_DISCOUNT (float): 52-week bank discount rate
            - 52WEEKS_COUPON_EQUIVALENT (float): 52-week coupon equivalent yield

        Notes:
            - 1 API call per request.
            - Included in All-In-One, EOD All World, EOD + Intraday All World Extended, Free plans.

        Examples:
            "Treasury bill rates for 2026" → get_ust_bill_rates(year=2026)
            "Latest T-bill rates" → get_ust_bill_rates()
            "T-bill rates for 2025, first 50 records" → get_ust_bill_rates(year=2025, limit=50)

        
        """
        url = f"{EODHD_API_BASE}/ust/bill-rates?1=1"

        if year is not None:
            try:
                y = int(year)
            except (ValueError, TypeError):
                raise ToolError("Parameter 'year' must be an integer (e.g. 2024).")
            if y < 1900:
                raise ToolError("Parameter 'year' must be >= 1900.")
            url += f"&filter[year]={y}"

        if limit is not None:
            try:
                lim = int(limit)
            except (ValueError, TypeError):
                raise ToolError("Parameter 'limit' must be a positive integer.")
            if lim <= 0:
                raise ToolError("Parameter 'limit' must be a positive integer.")
            url += f"&page[limit]={lim}"

        if offset is not None:
            try:
                off = int(offset)
            except (ValueError, TypeError):
                raise ToolError("Parameter 'offset' must be a non-negative integer.")
            if off < 0:
                raise ToolError("Parameter 'offset' must be a non-negative integer.")
            url += f"&page[offset]={off}"

        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
