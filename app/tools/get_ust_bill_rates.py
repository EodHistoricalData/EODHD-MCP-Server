# app/tools/get_ust_bill_rates.py


import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_query_param, build_url
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="US Treasury Bill Rates", readOnlyHint=True))
    async def get_ust_bill_rates(
        year: int | str | None = None,  # filter[year], e.g. 2024
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
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
            api_token (str, optional): Per-call token override.


        Returns:
            An envelope object with:
            - meta (object): { "total": int } — total number of records returned.
            - data (array): daily bill rate objects, each with:
                - date (str): observation date (YYYY-MM-DD)
                - tenor (str): bill tenor (e.g. 4WK, 8WK, 13WK, 17WK, 26WK, 52WK)
                - discount (float): discount rate
                - coupon (float): coupon-equivalent rate
                - avg_discount (float): average discount rate
                - avg_coupon (float): average coupon-equivalent rate
                - maturity_date (str): maturity date (YYYY-MM-DD)
                - cusip (str): CUSIP identifier
            - links (object): { "next": null } — always null; the full dataset for the year is
              returned and the endpoint does not paginate.

        Notes:
            - 1 API call per request.
            - Included in All-In-One, EOD All World, EOD + Intraday All World Extended, Free plans.
            - No pagination or date-range filtering: filter[year] is the only supported filter.

        Examples:
            "Treasury bill rates for 2026" → get_ust_bill_rates(year=2026)
            "Latest T-bill rates" → get_ust_bill_rates()
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
            "ust/bill-rates",
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
