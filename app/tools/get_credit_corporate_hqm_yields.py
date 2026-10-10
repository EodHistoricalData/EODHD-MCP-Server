# app/tools/get_credit_corporate_hqm_yields.py


import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import (
    build_query_param,
    build_url,
    coerce_date_param,
    coerce_page_params,
    split_csv,
    validate_date_range,
)
from app.response_formatter import (
    ResourceResponse,
    format_json_response,
    raise_on_api_error,
)

logger = logging.getLogger(__name__)

ALLOWED_TENORS = {1, 2, 3, 5, 7, 10, 15, 20, 25, 30}
ALLOWED_TYPES = {"par", "spot"}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Credit: Corporate HQM Yields", readOnlyHint=True))
    async def get_credit_corporate_hqm_yields(
        tenor: int | str | None = None,  # filter[tenor]: 1,2,3,5,7,10,15,20,25,30
        type: str | None = None,  # filter[type]: par | spot
        date_from: str | None = None,  # filter[from], YYYY-MM-DD
        date_to: str | None = None,  # filter[to], YYYY-MM-DD
        limit: int | str | None = None,  # page[limit], default 20, max 100
        offset: int | str | None = None,  # page[offset]
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch HQM (High Quality Market) corporate bond yield curves. Use when the user asks about
        HQM corporate yields, high-quality corporate bond spot or par yields, or yields by tenor.

        Returns HQM corporate bond yields by tenor (in years) and yield type (par or spot) over
        time. Filterable by tenor, type, and date range. Paginated.

        Args:
            tenor (int, optional): Tenor in years — one of 1, 2, 3, 5, 7, 10, 15, 20, 25, 30
                (or a comma-separated list, e.g. "5,10").
            type (str, optional): Yield type 'par' or 'spot' (or a comma-separated list).
            date_from (str, optional): Start date filter (YYYY-MM-DD).
            date_to (str, optional): End date filter (YYYY-MM-DD).
            limit (int, optional): Records per page (default 20, max 100).
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override.


        Returns:
            JSON envelope {data, meta, links}. Each data item:
            - series_id (str): HQM series identifier
            - tenor_years (int): tenor in years
            - yield_type (str): 'par' or 'spot'
            - as_of_date (str): observation date (ISO 8601 timestamp, e.g. 2026-06-01T00:00:00+00:00)
            - yield_value (float): yield value
            - source (str): data source

        Examples:
            "10-year HQM spot yield" → get_credit_corporate_hqm_yields(tenor=10, type="spot")
            "HQM par yields for 2025" → get_credit_corporate_hqm_yields(type="par", date_from="2025-01-01")
        """
        ten: str | None = None
        if tenor is not None:
            try:
                tenors = [int(t) for t in split_csv(tenor)]
            except (ValueError, TypeError):
                raise ToolError(
                    f"Parameter 'tenor' must be one (or a comma-separated list) of {sorted(ALLOWED_TENORS)}."
                )
            if not tenors or any(t not in ALLOWED_TENORS for t in tenors):
                raise ToolError(
                    f"Parameter 'tenor' must be one (or a comma-separated list) of {sorted(ALLOWED_TENORS)}."
                )
            ten = ",".join(str(t) for t in tenors)

        typ: str | None = None
        if type is not None:
            types = [t.lower() for t in split_csv(type)]
            if not types or any(t not in ALLOWED_TYPES for t in types):
                raise ToolError(f"Parameter 'type' must be one (or a comma-separated list) of {sorted(ALLOWED_TYPES)}.")
            typ = ",".join(types)

        date_from = coerce_date_param(date_from, "date_from")
        date_to = coerce_date_param(date_to, "date_to")
        validate_date_range(date_from, date_to, "date_from", "date_to")
        lim, off = coerce_page_params(limit, offset)

        url = build_url(
            "credit-risk/corporate/hqm-yields",
            {"api_token": api_token},
        )
        url += build_query_param("filter[tenor]", ten)
        url += build_query_param("filter[type]", typ)
        url += build_query_param("filter[from]", date_from)
        url += build_query_param("filter[to]", date_to)
        url += build_query_param("page[limit]", lim)
        url += build_query_param("page[offset]", off)

        data = await make_request(url)
        raise_on_api_error(data)

        return format_json_response(data)
