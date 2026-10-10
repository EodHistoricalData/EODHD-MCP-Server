# app/tools/get_credit_cds_market_aggregates.py


import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_query_param, build_url, coerce_date_param, coerce_page_params, validate_date_range
from app.response_formatter import (
    ResourceResponse,
    format_json_response,
    raise_on_api_error,
)

logger = logging.getLogger(__name__)

ALLOWED_METRICS = {"gross_notional"}
ALLOWED_DIMENSIONS = {"grade", "cleared_status"}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Credit: CDS Market Aggregates", readOnlyHint=True))
    async def get_credit_cds_market_aggregates(
        metric: str | None = None,  # filter[metric]: gross_notional
        dimension: str | None = None,  # filter[dimension]: grade | cleared_status
        value: str | None = None,  # filter[value]: breakdown value (e.g. a specific grade)
        region: str | None = None,  # filter[region]
        date_from: str | None = None,  # filter[from], YYYY-MM-DD
        date_to: str | None = None,  # filter[to], YYYY-MM-DD
        limit: int | str | None = None,  # page[limit], default 20, max 100
        offset: int | str | None = None,  # page[offset]
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch aggregated CDS market statistics. Use when the user asks about CDS market gross
        notional, CDS activity broken down by grade or cleared status, or CDS market size over time.

        Returns aggregated CDS market metrics (e.g. gross notional) broken down by a chosen
        dimension (grade or cleared status). Filterable by metric, dimension, and date range.
        Paginated.

        Args:
            metric (str, optional): Metric to aggregate. Currently 'gross_notional'.
            dimension (str, optional): Breakdown dimension: 'grade' or 'cleared_status'.
            value (str, optional): Filter by a specific breakdown value within the dimension.
            region (str, optional): Filter by region.
            date_from (str, optional): Start date filter (YYYY-MM-DD).
            date_to (str, optional): End date filter (YYYY-MM-DD).
            limit (int, optional): Records per page (default 20, max 100).
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override.


        Returns:
            JSON envelope {data, meta, links}. Each data item:
            - as_of_date (str): observation date (ISO 8601 timestamp, e.g. 2026-07-03T00:00:00+00:00)
            - release_date (str|null): data release date (ISO 8601 timestamp)
            - metric (str): metric name
            - breakdown_dimension (str): breakdown dimension
            - breakdown_value (str): breakdown value
            - region (str): region
            - usd_notional_mn (float): notional in USD millions
            - source (str): data source

        Examples:
            "CDS gross notional by grade" → get_credit_cds_market_aggregates(metric="gross_notional", dimension="grade")
            "CDS notional by cleared status" → get_credit_cds_market_aggregates(dimension="cleared_status")
        """
        if metric is not None and metric not in ALLOWED_METRICS:
            raise ToolError(f"Parameter 'metric' must be one of {sorted(ALLOWED_METRICS)}.")

        if dimension is not None and dimension not in ALLOWED_DIMENSIONS:
            raise ToolError(f"Parameter 'dimension' must be one of {sorted(ALLOWED_DIMENSIONS)}.")

        date_from = coerce_date_param(date_from, "date_from")
        date_to = coerce_date_param(date_to, "date_to")
        validate_date_range(date_from, date_to, "date_from", "date_to")
        lim, off = coerce_page_params(limit, offset)

        url = build_url(
            "credit-risk/cds-market/aggregates",
            {"api_token": api_token},
        )
        url += build_query_param("filter[metric]", metric)
        url += build_query_param("filter[dimension]", dimension)
        url += build_query_param("filter[value]", value)
        url += build_query_param("filter[region]", region)
        url += build_query_param("filter[from]", date_from)
        url += build_query_param("filter[to]", date_to)
        url += build_query_param("page[limit]", lim)
        url += build_query_param("page[offset]", off)

        data = await make_request(url)
        raise_on_api_error(data)

        return format_json_response(data)
