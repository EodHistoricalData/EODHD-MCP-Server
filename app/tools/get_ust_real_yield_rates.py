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
    @mcp.tool(annotations=ToolAnnotations(title="US Treasury Real Yield Rates", readOnlyHint=True))
    async def get_ust_real_yield_rates(
        year: int | str | None = None,  # filter[year], e.g. 2024
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
            api_token (str, optional): Per-call token override; env token used otherwise.


        Returns:
            An envelope object with:
            - meta (object): { "total": int } — total number of records returned.
            - data (array): daily real yield objects, each with:
                - date (str): observation date (YYYY-MM-DD)
                - tenor (str): maturity (e.g. 5Y, 7Y, 10Y, 20Y, 30Y)
                - rate (float): real (inflation-adjusted) yield for the given tenor
            - links (object): { "next": null } — always null; the full dataset for the year is
              returned and the endpoint does not paginate.

        Notes:
            - 1 API call per request.
            - Included in All-In-One, EOD All World, EOD + Intraday All World Extended, Free plans.
            - Compare with nominal yields for implied inflation expectations.
            - No pagination or date-range filtering: filter[year] is the only supported filter.

        Examples:
            "real yield rates for 2025" → get_ust_real_yield_rates(year=2025)
            "current real yield curve" → get_ust_real_yield_rates()
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
            "ust/real-yield-rates",
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
