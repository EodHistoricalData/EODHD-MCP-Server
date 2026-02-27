#get_mp_investverte_esg_list_sectors.py

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
    async def get_mp_investverte_esg_list_sectors(
        fmt: Optional[str] = "json",
        api_token: Optional[str] = None,  # per-call override
    ) -> str:
        """
        Get List of Sectors available in Investverte ESG dataset
        (GET /api/mp/investverte/sectors)

        Returns:
            A JSON-formatted string containing an array of objects:
            [
              {"sector": "Aerospace & Defense"},
              {"sector": "Airlines"},
              ...
            ]

        Notes:
            - This endpoint lists all sectors covered by the Investverte ESG dataset.
            - Rate limits (Marketplace product):
                * 100,000 API calls per 24 hours
                * 1,000 API requests per minute
                * 1 API request = 10 API calls
        """
        if fmt != "json":
            return _err("Only 'json' is supported by this tool.")

        # Base URL for Investverte sectors list
        url = f"{EODHD_API_BASE}/mp/investverte/sectors?fmt={fmt}"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            # Propagate API error message
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            # Expected: list of {"sector": "..."}
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected response format from API.")
