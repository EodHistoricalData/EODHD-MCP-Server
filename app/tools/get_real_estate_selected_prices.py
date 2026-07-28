# app/tools/get_real_estate_selected_prices.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import (
    build_query_param,
    build_url,
    coerce_page_params,
    coerce_quarter_param,
    sanitize_country_code,
    validate_quarter_range,
)
from app.response_formatter import (
    ResourceResponse,
    format_json_response,
    format_text_response,
    raise_on_api_error,
)

logger = logging.getLogger(__name__)

ALLOWED_TYPE = {"nominal", "real"}
ALLOWED_METRIC = {"index", "yoy"}
ALLOWED_SORT = {"period", "-period", "value", "-value"}
ALLOWED_FMT = {"json", "csv"}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Real Estate: Selected Property Prices", readOnlyHint=True))
    async def get_real_estate_selected_prices(
        code: str,
        type: str | None = None,  # filter[type]: nominal | real
        metric: str | None = None,  # filter[metric]: index | yoy
        from_period: str | None = None,  # filter[from]: 'YYYY-Qn' (e.g. 2020-Q1)
        to_period: str | None = None,  # filter[to]: 'YYYY-Qn'
        sort: str | None = None,  # period | -period | value | -value
        fmt: str = "json",  # json | csv
        limit: int | str | None = None,  # page[limit], 1..500 (default 50)
        offset: int | str | None = None,  # page[offset], >= 0 (default 0)
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Get Selected Property Prices (SPP) for a country — the headline harmonised
        residential property price series from the BIS Real Estate Data API.

        This is the top-level national series (nominal or real, as an index or year-on-year
        change). For granular breakdowns by area, property type, vintage, and frequency,
        use get_real_estate_detailed_prices instead. Discover available country codes with
        get_real_estate_countries. Consumes 5 API calls per request.

        Args:
            code (str): ISO alpha-2 country code, case-insensitive (e.g. 'US', 'us').
            type (str, optional): 'nominal' or 'real' (filter[type]).
            metric (str, optional): 'index' or 'yoy' (filter[metric]).
            from_period (str, optional): Start period 'YYYY-Qn', e.g. '2020-Q1' (filter[from]).
            to_period (str, optional): End period 'YYYY-Qn', e.g. '2024-Q4' (filter[to]).
            sort (str, optional): 'period', '-period', 'value', or '-value'.
            fmt (str): 'json' or 'csv'. Default 'json'.
            limit (int, optional): Records per page (page[limit]), 1..500. Default 50.
            offset (int, optional): Pagination offset (page[offset]), >= 0. Default 0.
            api_token (str, optional): Per-call token override. If not provided, env token is used.

        Returns:
            Envelope with:
            - data (array): each item with
                - period (str): observation period (e.g. '2024-Q1')
                - value (float): price index or year-on-year value
                - type (str): 'nominal' or 'real'
                - metric (str): 'index' or 'yoy'
            - meta (object): { country_code, country_name, type, metric, base_year,
              frequency, source, total, from, to, offset, limit }
            - links (object): { next } — next page URL or null

        Examples:
            "US real house price index" → get_real_estate_selected_prices(code="US", type="real", metric="index")
            "UK nominal YoY house prices since 2020" → get_real_estate_selected_prices(code="GB", type="nominal", metric="yoy", from_period="2020-Q1")
        """
        code = _normalize_country_code(code)

        if type is not None and type not in ALLOWED_TYPE:
            raise ToolError(f"Invalid 'type'. Allowed values: {sorted(ALLOWED_TYPE)}")

        if metric is not None and metric not in ALLOWED_METRIC:
            raise ToolError(f"Invalid 'metric'. Allowed values: {sorted(ALLOWED_METRIC)}")

        if sort is not None and sort not in ALLOWED_SORT:
            raise ToolError(f"Invalid 'sort'. Allowed values: {sorted(ALLOWED_SORT)}")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed values: {sorted(ALLOWED_FMT)}")

        from_period = coerce_quarter_param(from_period, "from_period")
        to_period = coerce_quarter_param(to_period, "to_period")
        validate_quarter_range(from_period, to_period)
        lim, off = coerce_page_params(limit, offset, max_limit=500)

        url = build_url(
            f"real-estate/{code}",
            {"sort": sort, "fmt": fmt, "api_token": api_token},
        )
        url += build_query_param("filter[type]", type)
        url += build_query_param("filter[metric]", metric)
        url += build_query_param("filter[from]", from_period)
        url += build_query_param("filter[to]", to_period)
        url += build_query_param("page[limit]", lim)
        url += build_query_param("page[offset]", off)

        data = await make_request(url, response_mode="text" if fmt == "csv" else "json")
        raise_on_api_error(data)

        if fmt == "csv":
            if not isinstance(data, str):
                raise ToolError("Unexpected CSV response format from API.")
            return format_text_response(data, "text/csv", resource_path=f"real-estate/{code}.csv")

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e


def _normalize_country_code(code: str) -> str:
    """Sanitize and upper-case an ISO alpha-2 country code (case-insensitive)."""
    return sanitize_country_code(code)
