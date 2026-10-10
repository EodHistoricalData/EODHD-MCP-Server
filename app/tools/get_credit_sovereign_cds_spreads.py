# app/tools/get_credit_sovereign_cds_spreads.py


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
    @mcp.tool(annotations=ToolAnnotations(title="Credit: Sovereign CDS Spreads", readOnlyHint=True))
    async def get_credit_sovereign_cds_spreads(
        country: str | None = None,  # filter[country], ISO-3 code(s), comma-separated
        as_of: str | None = None,  # filter[as_of], YYYY-MM-DD
        limit: int | str | None = None,  # page[limit], default 20, max 100
        offset: int | str | None = None,  # page[offset]
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch sovereign CDS (credit default swap) spreads by country. Use when the user asks about
        sovereign CDS spreads, default insurance costs for government debt, or CDS net of the
        Switzerland benchmark.

        Returns sovereign CDS spreads (raw and net of Switzerland) with Moody's rating context.
        Filterable by country and as-of date. Paginated.

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
            - cds_spread (float|null): sovereign CDS spread
            - cds_spread_net_of_switzerland (float|null): CDS spread net of Switzerland benchmark
            - source (str): data source

        Examples:
            "Italy sovereign CDS spread" → get_credit_sovereign_cds_spreads(country="ITA")
            "CDS spreads as of 2025-06-30" → get_credit_sovereign_cds_spreads(as_of="2025-06-30")
        """
        as_of = coerce_date_param(as_of, "as_of")
        lim, off = coerce_page_params(limit, offset)

        url = build_url(
            "credit-risk/sovereign/cds-spreads",
            {"api_token": api_token},
        )
        url += build_query_param("filter[country]", country)
        url += build_query_param("filter[as_of]", as_of)
        url += build_query_param("page[limit]", lim)
        url += build_query_param("page[offset]", off)

        data = await make_request(url)
        raise_on_api_error(data)

        return format_json_response(data)
