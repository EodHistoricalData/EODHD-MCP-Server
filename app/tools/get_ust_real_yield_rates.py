#get_ust_real_yield_rates.py

import json
from typing import Optional, Union

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_ust_real_yield_rates(
        year: Optional[Union[int, str]] = None,   # filter[year], e.g. 2024
        limit: Optional[Union[int, str]] = None,   # page[limit]
        offset: Optional[Union[int, str]] = None,  # page[offset]
        api_token: Optional[str] = None,            # per-call override
    ) -> str:
        """
        US Treasury Real Yield Rates API (Inflation-Adjusted)
        GET /api/ust/real-yield-rates

        Returns Daily Par Real Yield Curve Rates (inflation-adjusted yields).
        Tenors: 5Y, 7Y, 10Y, 20Y, 30Y.

        Args:
            year (int, optional): Filter by year (1900 to current+1). Defaults to current year.
            limit (int, optional): Records per page.
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override; env token used otherwise.

        Returns:
            JSON array of objects, each with:
            - date (str): Rate date, YYYY-MM-DD.
            - 5YR (str): 5-year real yield rate.
            - 7YR (str): 7-year real yield rate.
            - 10YR (str): 10-year real yield rate.
            - 20YR (str): 20-year real yield rate.
            - 30YR (str): 30-year real yield rate.

        Notes:
            - 1 API call per request.
            - Included in All-In-One, EOD All World, EOD + Intraday All World Extended, Free plans.
            - Compare with nominal yields for implied inflation expectations.
        """
        url = f"{EODHD_API_BASE}/ust/real-yield-rates?1=1"

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
