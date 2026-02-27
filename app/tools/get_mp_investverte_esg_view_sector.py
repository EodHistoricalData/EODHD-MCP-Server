#get_mp_investverte_esg_view_sector.py

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
    async def get_mp_investverte_esg_view_sector(
        symbol: str,                    # e.g., "Airlines"
        fmt: Optional[str] = "json",
        api_token: Optional[str] = None,  # per-call override
    ) -> str:
        """
        View ESG sector data for a specific sector
        (GET /api/mp/investverte/sector/{SYMBOL})

        Example:
            - /api/mp/investverte/sector/Airlines

        Response example:
            {
              "find": true,
              "industry": {
                "Airlines": [...],
                "Transportation": [...]
              },
              "years": ["2015-FY", "2015-Q1", ...]
            }

        Notes:
            - The 'industry' section contains sector/industry names mapped
              to ESG values over the 'years' axis.
            - Rate limits (Marketplace product):
                * 100,000 API calls per 24 hours
                * 1,000 API requests per minute
                * 1 API request = 10 API calls
        """
        if not symbol or not isinstance(symbol, str):
            return _err("Parameter 'symbol' is required and must be a non-empty string (e.g., 'Airlines').")

        if fmt != "json":
            return _err("Only 'json' is supported by this tool.")

        # Base URL for Investverte sector view endpoint
        url = f"{EODHD_API_BASE}/mp/investverte/sector/{symbol}?fmt={fmt}"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            # Propagate API error message
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            # Expected: dict with keys like "find", "industry", "years"
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected response format from API.")
