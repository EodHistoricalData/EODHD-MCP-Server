#get_cboe_indices_list.py

import json
from typing import Optional

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)


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

        Notes:
            - Pagination:
              If 'links.next' is not null, call that URL to get the next page.
            - Rate limits:
                * 10 API calls per request (CBOE dataset rule of thumb).
        """
        if fmt != "json":
            return _err("Only 'json' is supported by this tool.")

        # Base URL for CBOE indices list
        url = f"{EODHD_API_BASE}/cboe/indices?fmt={fmt}"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            # Propagate API error message
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            # Expected: dict with 'meta', 'data', 'links'
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected response format from API.")
