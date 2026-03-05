#get_cboe_index_data.py

import json
from typing import Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_cboe_index_data(
        index_code: str,             # e.g., "BDE30P"
        feed_type: str,              # e.g., "snapshot_official_closing"
        date: str,                   # YYYY-MM-DD, e.g., "2017-02-01"
        fmt: Optional[str] = "json",
        api_token: Optional[str] = None,  # per-call override
    ) -> str:
        """
        Get detailed CBOE index feed (index level + full components)
        (GET /api/cboe/index)

        Examples:
            - /api/cboe/index?filter[index_code]=BDE30P
              &filter[feed_type]=snapshot_official_closing
              &filter[date]=2017-02-01

        Required filters:
            - index_code: CBOE index code (e.g., BAT20N, BDE30P).
            - feed_type: CBOE feed type (e.g., snapshot_official_closing,
              snapshot_pro_forma_closing, etc.).
            - date: Trading date in YYYY-MM-DD format.

        Returns:
            Object with:
            - meta (object): total (int) — number of results
            - data (array): index feed objects, each with:
              - id (str): composite key (index_code-date-feed_type)
              - type (str): "cboe-index"
              - attributes (object):
                - region (str): geographic region
                - index_code (str): CBOE index code
                - feed_type (str): feed type
                - date (str): trading date (YYYY-MM-DD)
                - index_close (float): index closing value
                - index_divisor (float): index divisor
                - effective_date (str|null): effective date
                - review_date (str|null): review date
              - components (array): index constituents, each with:
                - id (str): component identifier
                - type (str): "cboe-index-component"
                - attributes (object):
                  - symbol (str): ticker symbol
                  - isin (str): ISIN code
                  - name (str): company name
                  - closing_price (float): component closing price
                  - currency (str): trading currency
                  - total_shares (int): total shares outstanding
                  - market_cap (float): market capitalization
                  - index_weighting (float): weight in index (%)
                  - index_value (float): contributed index value
                  - sector (str): industry sector

        Notes:
            - If required filters are missing, the API returns a JSON error
              under the "errors" key.
            - Rate limits: 10 API calls per request (dataset-specific rule of thumb).
        """
        # Basic validation
        if not index_code or not isinstance(index_code, str):
            raise ToolError(
                "Parameter 'index_code' is required and must be a non-empty string "
                "(e.g., 'BDE30P')."
            )

        if not feed_type or not isinstance(feed_type, str):
            raise ToolError(
                "Parameter 'feed_type' is required and must be a non-empty string "
                "(e.g., 'snapshot_official_closing')."
            )

        if not date or not isinstance(date, str):
            raise ToolError(
                "Parameter 'date' is required and must be a non-empty string "
                "in 'YYYY-MM-DD' format (e.g., '2017-02-01')."
            )

        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        # Build URL with deep-object-style filter params
        url = (
            f"{EODHD_API_BASE}/cboe/index"
            f"?filter[index_code]={index_code}"
            f"&filter[feed_type]={feed_type}"
            f"&filter[date]={date}"
            f"&fmt={fmt}"
        )
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            # Classic EODHD error envelope
            raise ToolError(str(data["error"]))

        try:
            # For both success and {"errors": {...}} cases, return pretty JSON
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
