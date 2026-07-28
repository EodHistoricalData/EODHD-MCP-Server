# app/tools/get_real_estate_countries.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_query_param, build_url
from app.response_formatter import (
    ResourceResponse,
    format_json_response,
    format_text_response,
    raise_on_api_error,
)

logger = logging.getLogger(__name__)

ALLOWED_SORT = {"code", "-code", "name", "-name"}
ALLOWED_FMT = {"json", "csv"}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Real Estate: Country Codes", readOnlyHint=True))
    async def get_real_estate_countries(
        sort: str | None = None,  # code | -code | name | -name
        fmt: str = "json",  # json | csv
        limit: int | str | None = None,  # page[limit], 1..500 (default 50)
        offset: int | str | None = None,  # page[offset], >= 0 (default 0)
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        List the countries covered by the EODHD Real Estate Data API (BIS residential
        property prices) and which datasets each country carries.

        Use this to discover available country codes before calling the other real-estate
        tools. Each country flags whether it has Selected Property Prices (SPP, headline
        harmonised series via get_real_estate_selected_prices) and Detailed Property
        Prices (DPP, granular national series via get_real_estate_detailed_prices).
        Consumes 5 API calls per request.

        Args:
            sort (str, optional): 'code', '-code', 'name', or '-name'.
            fmt (str): 'json' or 'csv'. Default 'json'.
            limit (int, optional): Records per page (page[limit]), 1..500. Default 50.
            offset (int, optional): Pagination offset (page[offset]), >= 0. Default 0.
            api_token (str, optional): Per-call token override. If not provided, env token is used.

        Returns:
            Envelope with:
            - data (array): each item with
                - code (str): ISO alpha-2 country code (e.g. 'US')
                - name (str): country name
                - has_spp (bool): Selected Property Prices available
                - has_dpp (bool): Detailed Property Prices available
            - meta (object): { total, offset, limit }
            - links (object): { next } — next page URL or null

        Examples:
            "Which countries have real estate data?" → get_real_estate_countries()
            "Countries sorted by name" → get_real_estate_countries(sort="name")
            "Second page of 100 countries" → get_real_estate_countries(limit=100, offset=100)
        """
        if sort is not None and sort not in ALLOWED_SORT:
            raise ToolError(f"Invalid 'sort'. Allowed values: {sorted(ALLOWED_SORT)}")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed values: {sorted(ALLOWED_FMT)}")

        lim = _coerce_limit(limit)
        off = _coerce_offset(offset)

        url = build_url(
            "real-estate/countries",
            {"sort": sort, "fmt": fmt, "api_token": api_token},
        )
        url += build_query_param("page[limit]", lim)
        url += build_query_param("page[offset]", off)

        data = await make_request(url, response_mode="text" if fmt == "csv" else "json")
        raise_on_api_error(data)

        if fmt == "csv":
            if not isinstance(data, str):
                raise ToolError("Unexpected CSV response format from API.")
            return format_text_response(data, "text/csv", resource_path="real-estate/countries.csv")

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e


def _coerce_limit(limit: int | str | None) -> int | None:
    if limit is None:
        return None
    try:
        lim = int(limit)
    except (ValueError, TypeError):
        raise ToolError("Parameter 'limit' must be an integer between 1 and 500.")
    if not (1 <= lim <= 500):
        raise ToolError("Parameter 'limit' must be between 1 and 500.")
    return lim


def _coerce_offset(offset: int | str | None) -> int | None:
    if offset is None:
        return None
    try:
        off = int(offset)
    except (ValueError, TypeError):
        raise ToolError("Parameter 'offset' must be a non-negative integer.")
    if off < 0:
        raise ToolError("Parameter 'offset' must be a non-negative integer.")
    return off
