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
        Get list of CBOE indices (Europe & regional families)
        (GET /api/cboe/indices)

        This endpoint returns:
            - EODHD index identifier (id, type)
            - CBOE index code
            - Region (country / market)
            - Latest feed type and date
            - Latest close value and index divisor
            - Pagination info via 'links.next'

        Example:
            /api/cboe/indices?api_token=XXXX&fmt=json

        Response example (trimmed):

            {
              "meta": {"total": 38},
              "data": [
                {
                  "id": "BEZ50N",
                  "type": "cboe-index",
                  "attributes": {
                    "region": "Eurozone",
                    "index_code": "BEZ50N",
                    "feed_type": "snapshot_official_closing",
                    "date": "2017-07-11",
                    "index_close": 15340.93,
                    "index_divisor": 149428673.477155
                  }
                },
                ...
              ],
              "links": {
                "next": null    # or URL to the next page
              }
            }

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
