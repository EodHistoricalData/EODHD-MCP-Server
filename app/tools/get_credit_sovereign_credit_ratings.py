# app/tools/get_credit_sovereign_credit_ratings.py


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
    @mcp.tool(annotations=ToolAnnotations(title="Credit: Sovereign Credit Ratings", readOnlyHint=True))
    async def get_credit_sovereign_credit_ratings(
        country: str | None = None,  # filter[country], ISO-3 code(s), comma-separated
        as_of: str | None = None,  # filter[as_of], YYYY-MM-DD
        limit: int | str | None = None,  # page[limit], default 20, max 100
        offset: int | str | None = None,  # page[offset]
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch sovereign credit ratings from the three major agencies. Use when the user asks about
        a country's credit rating, Moody's / S&P / Fitch sovereign ratings, or ratings comparisons
        across countries.

        Returns Moody's, S&P, and Fitch sovereign ratings by country. Filterable by country and
        as-of date. Paginated.

        Args:
            country (str, optional): Country ISO-3 code, or a comma-separated list of ISO-3 codes.
                Country names are NOT matched (upstream filters on ISO-3 only).
            as_of (str, optional): Filter by as-of date (YYYY-MM-DD).
            limit (int, optional): Records per page (default 20, max 100).
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override.


        Returns:
            JSON envelope {data, meta, links}. Each data item:
            - country_iso3 (str): ISO-3 country code
            - country_name (str): country name
            - as_of_date (str): as-of date (ISO 8601 timestamp, e.g. 2026-01-01T00:00:00+00:00)
            - moodys_rating (str|null): Moody's rating
            - sp_rating (str|null): S&P rating
            - fitch_rating (str|null): Fitch rating
            - source (str): data source

        Examples:
            "Germany credit rating" → get_credit_sovereign_credit_ratings(country="DEU")
            "Sovereign ratings as of 2025-01-01" → get_credit_sovereign_credit_ratings(as_of="2025-01-01")
        """
        as_of = coerce_date_param(as_of, "as_of")
        lim, off = coerce_page_params(limit, offset)

        url = build_url(
            "credit-risk/sovereign/credit-ratings",
            {"api_token": api_token},
        )
        url += build_query_param("filter[country]", country)
        url += build_query_param("filter[as_of]", as_of)
        url += build_query_param("page[limit]", lim)
        url += build_query_param("page[offset]", off)

        data = await make_request(url)
        raise_on_api_error(data)

        return format_json_response(data)
