# get_ust_yield_rates.py

import json

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_ust_yield_rates(
        year: int | str | None = None,  # filter[year], e.g. 2024
        limit: int | str | None = None,  # page[limit]
        offset: int | str | None = None,  # page[offset]
        api_token: str | None = None,  # per-call override
    ) -> str:
        """

        Fetch daily US Treasury par yield curve rates. Use when the user asks about Treasury
        yields, the yield curve, government bond rates, or interest rates across maturities.

        Returns nominal par yield curve rates for tenors: 1M, 1.5M, 2M, 3M, 4M, 6M, 1Y, 2Y,
        3Y, 5Y, 7Y, 10Y, 20Y, 30Y. Fields include date, tenor, and rate. Filterable by year.
        Costs 1 API call per request.

        For short-term T-bill discount/coupon rates (4WK-52WK), use get_ust_bill_rates instead.

        Args:
            year (int, optional): Filter by year (1900+). Defaults to current year.
            limit (int, optional): Records per page.
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override.


        Returns:
            Array of daily yield rate objects, each with:
            - date (str): observation date (YYYY-MM-DD)
            - 1MO (float): 1-month yield
            - 2MO (float): 2-month yield
            - 3MO (float): 3-month yield
            - 4MO (float): 4-month yield
            - 6MO (float): 6-month yield
            - 1YR (float): 1-year yield
            - 2YR (float): 2-year yield
            - 3YR (float): 3-year yield
            - 5YR (float): 5-year yield
            - 7YR (float): 7-year yield
            - 10YR (float): 10-year yield
            - 20YR (float): 20-year yield
            - 30YR (float): 30-year yield

        Notes:
            - 1 API call per request.
            - Included in All-In-One, EOD All World, EOD + Intraday All World Extended, Free plans.
            - Full yield curve across multiple maturities.

        Examples:
            "US Treasury yield curve for 2026" → get_ust_yield_rates(year=2026)
            "Current yield rates" → get_ust_yield_rates()
            "2025 yield rates, page 2" → get_ust_yield_rates(year=2025, offset=100, limit=100)

        
        """
        url = f"{EODHD_API_BASE}/ust/yield-rates?1=1"

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
