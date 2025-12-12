#get_mp_investverte_esg_list_countries.py

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
    async def get_mp_investverte_esg_list_countries(
        fmt: Optional[str] = "json",
        api_token: Optional[str] = None,  # per-call override
    ) -> str:
        """
        Get List of Countries available in Investverte ESG dataset
        (GET /api/mp/investverte/countries)

        Returns:
            A JSON-formatted string containing an array of objects:
            [
              {"country_code": "AD", "country_descr": "Andorra"},
              {"country_code": "AE", "country_descr": "United Arab Emirates"},
              ...
            ]

        Notes:
            - This endpoint lists all countries covered by the Investverte ESG dataset.
            - Rate limits (Marketplace product):
                * 100,000 API calls per 24 hours
                * 1,000 API requests per minute
                * 1 API request = 10 API calls
        """
        if fmt != "json":
            return _err("Only 'json' is supported by this tool.")

        # Base URL for Investverte countries list
        url = f"{EODHD_API_BASE}/mp/investverte/countries?fmt={fmt}"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            # Propagate API error message
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            # Expected: list of {"country_code": ..., "country_descr": ...}
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected response format from API.")
