# app/tools/get_real_estate_detailed_prices.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_query_param, build_url, sanitize_exchange
from app.response_formatter import (
    ResourceResponse,
    format_json_response,
    format_text_response,
    raise_on_api_error,
)

logger = logging.getLogger(__name__)

ALLOWED_FREQ = {"Q", "A", "M", "H"}
ALLOWED_SORT = {"period", "-period", "value", "-value"}
ALLOWED_FMT = {"json", "csv"}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Real Estate: Detailed Property Prices", readOnlyHint=True))
    async def get_real_estate_detailed_prices(
        code: str,
        area: str | None = None,  # filter[area]: BIS covered-area dimension code
        property_type: str | None = None,  # filter[property_type]
        vintage: str | None = None,  # filter[vintage]
        freq: str | None = None,  # filter[freq]: Q | A | M | H
        from_period: str | None = None,  # filter[from]: period (e.g. 2020-01 or 2020-Q1)
        to_period: str | None = None,  # filter[to]
        sort: str | None = None,  # period | -period | value | -value
        fmt: str = "json",  # json | csv
        limit: int | str | None = None,  # page[limit], 1..500 (default 50)
        offset: int | str | None = None,  # page[offset], >= 0 (default 0)
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Get Detailed Property Prices (DPP) for a country — the granular national residential
        property price series from the BIS Real Estate Data API, broken down by covered area,
        property type, vintage (new vs existing), and frequency.

        Use this for detailed analysis beyond the headline series returned by
        get_real_estate_selected_prices. Discover the available series combinations for a
        country with get_real_estate_detailed_series, and available country codes with
        get_real_estate_countries. Consumes 5 API calls per request.

        Args:
            code (str): ISO alpha-2 country code, case-insensitive (e.g. 'AE', 'ae').
            area (str, optional): BIS covered-area dimension code (filter[area]).
            property_type (str, optional): Property type code (filter[property_type]).
            vintage (str, optional): Vintage code, e.g. new vs existing dwellings (filter[vintage]).
            freq (str, optional): 'Q', 'A', 'M', or 'H' (filter[freq]).
            from_period (str, optional): Start period following the series frequency,
              e.g. '2020-01' or '2020-Q1' (filter[from]).
            to_period (str, optional): End period (filter[to]).
            sort (str, optional): 'period', '-period', 'value', or '-value'.
            fmt (str): 'json' or 'csv'. Default 'json'.
            limit (int, optional): Records per page (page[limit]), 1..500. Default 50.
            offset (int, optional): Pagination offset (page[offset]), >= 0. Default 0.
            api_token (str, optional): Per-call token override. If not provided, env token is used.

        Returns:
            Envelope with:
            - data (array): each item with
                - period (str): observation period
                - value (float): series value
                - frequency (str): series frequency
                - covered_area (str), covered_area_label (str)
                - property_type (str), property_type_label (str)
                - vintage (str), vintage_label (str)
                - unit_measure (str), unit_measure_label (str | null)
            - meta (object): { country_code, source, dataset, total, offset, limit, filters }
            - links (object): { next } — next page URL or null

        Examples:
            "Detailed UAE house prices for property type 1" → get_real_estate_detailed_prices(code="AE", property_type="1")
            "Quarterly detailed US series" → get_real_estate_detailed_prices(code="US", freq="Q")
        """
        code = _normalize_country_code(code)

        if freq is not None and freq not in ALLOWED_FREQ:
            raise ToolError(f"Invalid 'freq'. Allowed values: {sorted(ALLOWED_FREQ)}")

        if sort is not None and sort not in ALLOWED_SORT:
            raise ToolError(f"Invalid 'sort'. Allowed values: {sorted(ALLOWED_SORT)}")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed values: {sorted(ALLOWED_FMT)}")

        lim = _coerce_limit(limit)
        off = _coerce_offset(offset)

        url = build_url(
            f"real-estate/{code}/detailed",
            {"sort": sort, "fmt": fmt, "api_token": api_token},
        )
        url += build_query_param("filter[area]", area)
        url += build_query_param("filter[property_type]", property_type)
        url += build_query_param("filter[vintage]", vintage)
        url += build_query_param("filter[freq]", freq)
        url += build_query_param("filter[from]", from_period)
        url += build_query_param("filter[to]", to_period)
        url += build_query_param("page[limit]", lim)
        url += build_query_param("page[offset]", off)

        data = await make_request(url, response_mode="text" if fmt == "csv" else "json")
        raise_on_api_error(data)

        if fmt == "csv":
            if not isinstance(data, str):
                raise ToolError("Unexpected CSV response format from API.")
            return format_text_response(data, "text/csv", resource_path=f"real-estate/{code}/detailed.csv")

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e


def _normalize_country_code(code: str) -> str:
    """Sanitize and upper-case an ISO alpha-2 country code (case-insensitive)."""
    return sanitize_exchange(code, "code").upper()


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
