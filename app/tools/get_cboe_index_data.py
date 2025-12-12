#get_cboe_index_data.py

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
            JSON-formatted string of the raw API response, e.g.:

            {
              "meta": { "total": 1 },
              "data": [
                {
                  "id": "BDE30P-2017-02-01-snapshot_official_closing",
                  "type": "cboe-index",
                  "attributes": {
                    "region": "Germany",
                    "index_code": "BDE30P",
                    "feed_type": "snapshot_official_closing",
                    "date": "2017-02-01",
                    "index_close": 13915.57,
                    "index_divisor": 68033376.886244,
                    "effective_date": null,
                    "review_date": null
                  },
                  "components": [
                    {
                      "id": "...-HEI.DU",
                      "type": "cboe-index-component",
                      "attributes": {
                        "symbol": "HEI.DU",
                        "isin": "DE0006047004",
                        "name": "HEIDELBERGCEMENT AG",
                        "closing_price": 90.15,
                        "currency": "EUR",
                        "total_shares": 198416477,
                        "market_cap": 17887245401.55,
                        "index_weighting": 1.360357,
                        "index_value": 189.301447,
                        "sector": "Non-Energy Materials",
                        ...
                      }
                    },
                    ...
                  ]
                }
              ]
            }

        Notes:
            - If required filters are missing, the API returns a JSON error
              under the "errors" key.
            - Rate limits: 10 API calls per request (dataset-specific rule of thumb).
        """
        # Basic validation
        if not index_code or not isinstance(index_code, str):
            return _err(
                "Parameter 'index_code' is required and must be a non-empty string "
                "(e.g., 'BDE30P')."
            )

        if not feed_type or not isinstance(feed_type, str):
            return _err(
                "Parameter 'feed_type' is required and must be a non-empty string "
                "(e.g., 'snapshot_official_closing')."
            )

        if not date or not isinstance(date, str):
            return _err(
                "Parameter 'date' is required and must be a non-empty string "
                "in 'YYYY-MM-DD' format (e.g., '2017-02-01')."
            )

        if fmt != "json":
            return _err("Only 'json' is supported by this tool.")

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
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            # Classic EODHD error envelope
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            # For both success and {"errors": {...}} cases, return pretty JSON
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected response format from API.")
