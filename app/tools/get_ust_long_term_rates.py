# app/tools/get_ust_long_term_rates.py


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
    async def get_ust_long_term_rates(
        year: int | str | None = None,  # filter[year], e.g. 2024
        limit: int | str | None = None,  # page[limit]
        offset: int | str | None = None,  # page[offset]
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch US Treasury long-term rate composites and averages. Use when asked about 20-year bond
        constant maturity rates, long-term real rate averages, or extrapolation factors.
        Covers rate types: BC_20year, Over_10_Years, Real_Rate — combining daily long-term
        nominal rates with real long-term rate averages.
        For individual tenor yield curves use get_ust_yield_rates. For inflation-adjusted
        real yields use get_ust_real_yield_rates. For T-bill rates use get_ust_bill_rates.
        Consumes 1 API call per request.

        Args:
            year (int, optional): Filter by year (1900 to current+1). Defaults to current year.
            limit (int, optional): Records per page.
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override; env token used otherwise.


        Returns:
            JSON array of objects, each with:
            - date (str): Rate date, YYYY-MM-DD.
            - LT_COMPOSITE_RATE (str): Long-term composite rate.
            - TREASURY_20YR (str): Treasury 20-year rate.
            - BC_20YEAR (str): Bond-equivalent 20-year rate.
            - EXTRAPOLATION_FACTOR_20YR (str): Extrapolation factor for 20-year maturity.

        Notes:
            - 1 API call per request.
            - Included in All-In-One, EOD All World, EOD + Intraday All World Extended, Free plans.
            - Combines "Daily Treasury Real Long-Term Rate Averages" and
              "Daily Treasury Long-Term Rates".

        Examples:
            "long-term treasury rates for 2024" → year=2024
            "20-year bond rates this year, first 20 records" → year=2026, limit=20
            "real long-term rate averages for 2022" → year=2022
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
            "ust/long-term-rates",
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
