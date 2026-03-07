#get_cboe_indices_list.py

import json
from typing import Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_cboe_indices_list(
        fmt: Optional[str] = "json",
        api_token: Optional[str] = None,  # per-call override
    ) -> str:
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

        # Base URL for CBOE indices list
        url = f"{EODHD_API_BASE}/cboe/indices?fmt={fmt}"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            # Propagate API error message
            raise ToolError(str(data["error"]))

        try:
            # Expected: dict with 'meta', 'data', 'links'
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
