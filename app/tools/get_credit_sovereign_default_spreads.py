# app/tools/get_credit_sovereign_default_spreads.py


import logging

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_query_param, build_url, coerce_date_param, coerce_page_params
from app.response_formatter import (
    ResourceResponse,
    format_json_response,
    raise_on_api_error,
)

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Credit: Sovereign Default Spreads", readOnlyHint=True))
    async def get_credit_sovereign_default_spreads(
        rating: str | None = None,  # filter[rating], e.g. Aaa, Baa2
        as_of: str | None = None,  # filter[as_of], YYYY-MM-DD
        limit: int | str | None = None,  # page[limit], default 20, max 100
        offset: int | str | None = None,  # page[offset]
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch default spreads by credit rating. Use when the user asks about the default spread
        associated with a given rating (e.g. Aaa, Baa2), or the rating-to-spread mapping used to
        derive country risk premiums.

        Returns the default spread for each rating bucket. Filterable by rating and as-of date.
        Paginated.

        Args:
            rating (str, optional): Filter by rating (e.g. 'Aaa', 'Baa2').
            as_of (str, optional): Filter by as-of date (YYYY-MM-DD).
            limit (int, optional): Records per page (default 20, max 100).
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override.


        Returns:
            JSON envelope {data, meta, links}. Each data item:
            - rating (str): credit rating bucket
            - as_of_date (str): as-of date (ISO 8601 timestamp, e.g. 2026-01-01T00:00:00+00:00)
            - default_spread (float): default spread for the rating
            - source (str): data source

        Examples:
            "Default spread for Baa2" → get_credit_sovereign_default_spreads(rating="Baa2")
            "Rating default spreads as of 2025-01-01" → get_credit_sovereign_default_spreads(as_of="2025-01-01")
        """
        as_of = coerce_date_param(as_of, "as_of")
        lim, off = coerce_page_params(limit, offset)

        url = build_url(
            "credit-risk/sovereign/default-spreads",
            {"api_token": api_token},
        )
        url += build_query_param("filter[rating]", rating)
        url += build_query_param("filter[as_of]", as_of)
        url += build_query_param("page[limit]", lim)
        url += build_query_param("page[offset]", off)

        data = await make_request(url)
        raise_on_api_error(data)

        return format_json_response(data)
