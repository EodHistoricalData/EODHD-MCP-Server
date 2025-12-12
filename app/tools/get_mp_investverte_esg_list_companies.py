#get_mp_investverte_esg_list_companies.py

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
    async def get_mp_investverte_esg_list_companies(
        fmt: Optional[str] = "json",
        api_token: Optional[str] = None,  # per-call override
    ) -> str:
        """
        Get List of Companies available in Investverte ESG dataset
        (GET /api/mp/investverte/companies)

        Returns:
            A JSON-formatted string containing an array of objects:
            [
              {"symbol": "000001.SZ", "name": "Ping An Bank Co., Ltd."},
              {"symbol": "000002.SZ", "name": "China Vanke Co., Ltd."},
              ...
            ]

        Notes:
            - This endpoint lists all companies covered by the Investverte ESG dataset.
            - Rate limits (Marketplace product):
                * 100,000 API calls per 24 hours
                * 1,000 API requests per minute
                * 1 API request = 10 API calls
        """
        if fmt != "json":
            return _err("Only 'json' is supported by this tool.")

        # Base URL for Investverte companies list
        url = f"{EODHD_API_BASE}/mp/investverte/companies?fmt={fmt}"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            # Propagate API error message
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            # Expected: list of {"symbol": ..., "name": ...}
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected response format from API.")
