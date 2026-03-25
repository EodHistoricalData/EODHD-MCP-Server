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
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_ust_bill_rates(
        year: int | str | None = None,  # filter[year], e.g. 2024
        limit: int | str | None = None,  # page[limit]
        offset: int | str | None = None,  # page[offset]
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
            limit (int, optional): Records per page.
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override.


        Returns:
            Array of daily bill rate objects, each with:
            - date (str): observation date (YYYY-MM-DD)
            - 4WEEKS_BANK_DISCOUNT (float): 4-week bank discount rate
            - 4WEEKS_COUPON_EQUIVALENT (float): 4-week coupon equivalent yield
            - 8WEEKS_BANK_DISCOUNT (float): 8-week bank discount rate
            - 8WEEKS_COUPON_EQUIVALENT (float): 8-week coupon equivalent yield
            - 13WEEKS_BANK_DISCOUNT (float): 13-week bank discount rate
            - 13WEEKS_COUPON_EQUIVALENT (float): 13-week coupon equivalent yield
            - 17WEEKS_BANK_DISCOUNT (float): 17-week bank discount rate
            - 17WEEKS_COUPON_EQUIVALENT (float): 17-week coupon equivalent yield
            - 26WEEKS_BANK_DISCOUNT (float): 26-week bank discount rate
            - 26WEEKS_COUPON_EQUIVALENT (float): 26-week coupon equivalent yield
            - 52WEEKS_BANK_DISCOUNT (float): 52-week bank discount rate
            - 52WEEKS_COUPON_EQUIVALENT (float): 52-week coupon equivalent yield

        Notes:
            - 1 API call per request.
            - Included in All-In-One, EOD All World, EOD + Intraday All World Extended, Free plans.

        Examples:
            "Treasury bill rates for 2026" → get_ust_bill_rates(year=2026)
            "Latest T-bill rates" → get_ust_bill_rates()
            "T-bill rates for 2025, first 50 records" → get_ust_bill_rates(year=2025, limit=50)
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
            "ust/bill-rates",
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
