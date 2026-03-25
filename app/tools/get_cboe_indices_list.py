# app/tools/get_cboe_indices_list.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_cboe_indices_list(
        fmt: str | None = "json",
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        List all available CBOE indices with their latest values. Use when the user wants to
        browse CBOE European and regional index families, check which CBOE indices are available,
        or find a CBOE index code.

        Returns index codes, regions, latest close values, index divisors, and feed metadata
        for ~38 CBOE indices. Paginated via 'links.next'. Costs 10 API calls per request.

        For detailed component-level data on a specific CBOE index, use get_cboe_index_data.

        Returns:
            Object with:
            - meta (object): total (int) — total number of indices
            - data (array): index objects, each with:
              - id (str): CBOE index identifier
              - type (str): always "cboe-index"
              - attributes (object):
                - region (str): geographic region (e.g. "Eurozone", "Germany")
                - index_code (str): CBOE index code
                - feed_type (str): feed type (e.g. "snapshot_official_closing")
                - date (str): latest date (YYYY-MM-DD)
                - index_close (float): latest closing value
                - index_divisor (float): index divisor
            - links (object): next (str|null) — URL for next page, null if last

        Notes:
            - Pagination:
              If 'links.next' is not null, call that URL to get the next page.
            - Rate limits:
                * 10 API calls per request (CBOE dataset rule of thumb).

        Examples:
            "List all CBOE indices" → get_cboe_indices_list()
            "What CBOE European indices are available?" → get_cboe_indices_list()
        """
        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        url = build_url("cboe/indices", {"fmt": fmt, "api_token": api_token})

        data = await make_request(url)

        try:
            # Expected: dict with 'meta', 'data', 'links'
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
