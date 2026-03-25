# app/tools/get_ust_real_yield_rates.py


import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_query_param, build_url
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_ust_real_yield_rates(
        year: int | str | None = None,  # filter[year], e.g. 2024
        limit: int | str | None = None,  # page[limit]
        offset: int | str | None = None,  # page[offset]
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch US Treasury inflation-adjusted (real) yield curve rates. Use when asked about TIPS yields,
        real interest rates, or inflation-adjusted Treasury returns.
        Covers 5Y, 7Y, 10Y, 20Y, 30Y tenors from the Daily Par Real Yield Curve.
        For nominal Treasury yields use get_ust_yield_rates. For T-bill discount rates use get_ust_bill_rates.
        For long-term rate averages (20Y+ composites) use get_ust_long_term_rates.
        Consumes 1 API call per request.

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

        Examples:
            "real yield rates for 2025" → year=2025
            "last 10 inflation-adjusted treasury yields" → limit=10
            "real yield curve data for 2023, page 2" → year=2023, limit=50, offset=50
        """
        y: int | None = None
        if year is not None:
            try:
                y = int(year)
            except (ValueError, TypeError):
                raise ToolError("Parameter 'year' must be an integer (e.g. 2024).")
            if y < 1900:
                raise ToolError("Parameter 'year' must be >= 1900.")

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
            "ust/real-yield-rates",
            {"api_token": api_token},
        )
        url += build_query_param("filter[year]", y)
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
