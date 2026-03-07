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
        Fetch detailed data for a specific CBOE index on a given date, including all constituent
        components. Use when the user needs index close value, divisor, and full component
        breakdown (symbols, weights, market caps, sectors) for a CBOE index.

        Requires index_code, feed_type, and date. Returns index-level attributes plus an array
        of components with ISIN, closing price, currency, shares, market cap, weighting, and
        sector. Costs 10 API calls per request.

        For listing all available CBOE indices, use get_cboe_indices_list first.

        Args:
            index_code (str): CBOE index code (e.g., 'BDE30P', 'BAT20N').
            feed_type (str): Feed type (e.g., 'snapshot_official_closing').
            date (str): Trading date in YYYY-MM-DD format.
            fmt (str): 'json' only (default).
            api_token (str, optional): Per-call token override.


        Examples:
            - /api/cboe/index?filter[index_code]=BDE30P
              &filter[feed_type]=snapshot_official_closing
              &filter[date]=2017-02-01

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
