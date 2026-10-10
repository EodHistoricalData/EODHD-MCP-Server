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
    @mcp.tool(annotations=ToolAnnotations(title="US Treasury Long-Term Rates", readOnlyHint=True))
    async def get_ust_long_term_rates(
        year: int | str | None = None,  # filter[year], e.g. 2024
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
            api_token (str, optional): Per-call token override; env token used otherwise.


        Returns:
            An envelope object with:
            - meta (object): { "total": int } — total number of records returned.
            - data (array): daily long-term rate objects, each with:
                - date (str): observation date (YYYY-MM-DD)
                - rate_type (str): rate series identifier (e.g. BC_20year, Over_10_Years, Real_Rate)
                - rate (float): rate value
                - extrapolation_factor (float or null): extrapolation factor where applicable
            - links (object): { "next": null } — always null; the full dataset for the year is
              returned and the endpoint does not paginate.

        Notes:
            - 1 API call per request.
            - Included in All-In-One, EOD All World, EOD + Intraday All World Extended, Free plans.
            - Combines "Daily Treasury Real Long-Term Rate Averages" and
              "Daily Treasury Long-Term Rates".
            - No pagination or date-range filtering: filter[year] is the only supported filter.

        Examples:
            "long-term treasury rates for 2024" → get_ust_long_term_rates(year=2024)
            "20-year bond rates this year" → get_ust_long_term_rates(year=2026)
            "real long-term rate averages for 2022" → get_ust_long_term_rates(year=2022)
        """
        y: int | None = None
        if year is not None:
            try:
                y = int(year)
            except (ValueError, TypeError):
                raise ToolError("Parameter 'year' must be an integer (e.g. 2024).")
            if y < 1900:
                raise ToolError("Parameter 'year' must be >= 1900.")

        url = build_url(
            "ust/long-term-rates",
            {"api_token": api_token},
        )
        url += build_query_param("filter[year]", y)

        data = await make_request(url)

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
