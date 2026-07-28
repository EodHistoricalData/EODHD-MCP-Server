# app/tools/get_ust_yield_rates.py


import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_query_param, build_url
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="US Treasury Par Yield Rates", readOnlyHint=True))
    async def get_ust_yield_rates(
        year: int | str | None = None,  # filter[year], e.g. 2024
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch daily US Treasury par yield curve rates. Use when the user asks about Treasury
        yields, the yield curve, government bond rates, or interest rates across maturities.

        Returns nominal par yield curve rates for tenors: 1M, 1.5M, 2M, 3M, 4M, 6M, 1Y, 2Y,
        3Y, 5Y, 7Y, 10Y, 20Y, 30Y. Fields include date, tenor, and rate. Filterable by year.
        Costs 1 API call per request.

        For short-term T-bill discount/coupon rates (4WK-52WK), use get_ust_bill_rates instead.

        Args:
            year (int, optional): Filter by year (1900+). Defaults to current year.
            api_token (str, optional): Per-call token override.


        Returns:
            An envelope object with:
            - meta (object): { "total": int } — total number of records returned.
            - data (array): daily yield rate objects, each with:
                - date (str): observation date (YYYY-MM-DD)
                - tenor (str): maturity (e.g. 1M, 1.5M, 2M, 3M, 4M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y)
                - rate (float): par yield for the given tenor
            - links (object): { "next": null } — always null; the full dataset for the year is
              returned and the endpoint does not paginate.

        Notes:
            - 1 API call per request.
            - Included in All-In-One, EOD All World, EOD + Intraday All World Extended, Free plans.
            - Full yield curve across multiple maturities.
            - No pagination or date-range filtering: filter[year] is the only supported filter.

        Examples:
            "US Treasury yield curve for 2026" → get_ust_yield_rates(year=2026)
            "Current yield rates" → get_ust_yield_rates()
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
            "ust/yield-rates",
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
