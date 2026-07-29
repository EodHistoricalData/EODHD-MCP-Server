# app/tools/get_credit_corporate_cmdi.py


import logging

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_query_param, build_url, coerce_date_param, coerce_page_params, validate_date_range
from app.response_formatter import (
    ResourceResponse,
    format_json_response,
    raise_on_api_error,
)

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Credit: Corporate CMDI", readOnlyHint=True))
    async def get_credit_corporate_cmdi(
        date_from: str | None = None,  # filter[from], YYYY-MM-DD
        date_to: str | None = None,  # filter[to], YYYY-MM-DD
        limit: int | str | None = None,  # page[limit], default 20, max 100
        offset: int | str | None = None,  # page[offset]
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch the Corporate Market-based Default Indicator (CMDI) time series. Use when the user asks
        about corporate credit stress, the CMDI index, or investment-grade vs high-yield market
        default indicators.

        Returns the market CMDI along with investment-grade (IG) and high-yield (HY) sub-indices
        over time. Filterable by date range. Paginated.

        Args:
            date_from (str, optional): Start date filter (YYYY-MM-DD).
            date_to (str, optional): End date filter (YYYY-MM-DD).
            limit (int, optional): Records per page (default 20, max 100).
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override.


        Returns:
            JSON envelope {data, meta, links}. Each data item:
            - as_of_date (str): observation date (ISO 8601 timestamp, e.g. 2026-06-19T00:00:00+00:00)
            - market_cmdi (float|null): overall market CMDI
            - ig_cmdi (float|null): investment-grade CMDI
            - hy_cmdi (float|null): high-yield CMDI
            - source (str): data source

        Examples:
            "Corporate CMDI for 2025" → get_credit_corporate_cmdi(date_from="2025-01-01", date_to="2025-12-31")
            "Latest CMDI" → get_credit_corporate_cmdi()
        """
        date_from = coerce_date_param(date_from, "date_from")
        date_to = coerce_date_param(date_to, "date_to")
        validate_date_range(date_from, date_to, "date_from", "date_to")
        lim, off = coerce_page_params(limit, offset)

        url = build_url(
            "credit-risk/corporate/cmdi",
            {"api_token": api_token},
        )
        url += build_query_param("filter[from]", date_from)
        url += build_query_param("filter[to]", date_to)
        url += build_query_param("page[limit]", lim)
        url += build_query_param("page[offset]", off)

        data = await make_request(url)
        raise_on_api_error(data)

        return format_json_response(data)
