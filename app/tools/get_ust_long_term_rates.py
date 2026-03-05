#get_ust_long_term_rates.py

import json
from typing import Optional, Union

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_ust_long_term_rates(
        year: Optional[Union[int, str]] = None,   # filter[year], e.g. 2024
        limit: Optional[Union[int, str]] = None,   # page[limit]
        offset: Optional[Union[int, str]] = None,  # page[offset]
        api_token: Optional[str] = None,            # per-call override
    ) -> str:
        """
        US Treasury Long-Term Rates API
        GET /api/ust/long-term-rates

        Returns Daily Treasury Long-Term Rates and Real Long-Term Rate Averages.
        Rate types: BC_20year, Over_10_Years, Real_Rate.

        Args:
            year (int, optional): Filter by year (1900 to current+1). Defaults to current year.
            limit (int, optional): Records per page.
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override; env token used otherwise.

        Notes:
            - 1 API call per request.
            - Included in All-In-One, EOD All World, EOD + Intraday All World Extended, Free plans.
            - Response fields: date, rate_type, rate, extrapolation_factor.
            - Combines "Daily Treasury Real Long-Term Rate Averages" and
              "Daily Treasury Long-Term Rates".
        """
        url = f"{EODHD_API_BASE}/ust/long-term-rates?1=1"

        if year is not None:
            try:
                y = int(year)
            except (ValueError, TypeError):
                return _err("Parameter 'year' must be an integer (e.g. 2024).")
            if y < 1900:
                return _err("Parameter 'year' must be >= 1900.")
            url += f"&filter[year]={y}"

        if limit is not None:
            try:
                lim = int(limit)
            except (ValueError, TypeError):
                return _err("Parameter 'limit' must be a positive integer.")
            if lim <= 0:
                return _err("Parameter 'limit' must be a positive integer.")
            url += f"&page[limit]={lim}"

        if offset is not None:
            try:
                off = int(offset)
            except (ValueError, TypeError):
                return _err("Parameter 'offset' must be a non-negative integer.")
            if off < 0:
                return _err("Parameter 'offset' must be a non-negative integer.")
            url += f"&page[offset]={off}"

        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected response format from API.")
