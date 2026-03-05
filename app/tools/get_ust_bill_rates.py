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
        US Treasury Bill Rates API
        GET /api/ust/bill-rates

        Returns Daily Treasury Bill Rates (discount and coupon-equivalent).
        Tenors: 4WK, 8WK, 13WK, 17WK, 26WK, 52WK.

        Args:
            year (int, optional): Filter by year (1900 to current+1). Defaults to current year.
            limit (int, optional): Records per page.
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override; env token used otherwise.

        Notes:
            - 1 API call per request.
            - Included in All-In-One, EOD All World, EOD + Intraday All World Extended, Free plans.
            - Response fields: date, tenor, discount, coupon, avg_discount, avg_coupon,
              maturity_date, cusip.

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
