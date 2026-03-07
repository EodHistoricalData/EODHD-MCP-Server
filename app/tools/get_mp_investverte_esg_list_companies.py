#get_mp_investverte_esg_list_companies.py

import json
from typing import Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_investverte_esg_list_companies(
        fmt: Optional[str] = "json",
        api_token: Optional[str] = None,  # per-call override
    ) -> str:
        """
        [InvestVerte] List all companies available in the ESG dataset.
        Returns an array of symbol/name pairs for every company with ESG coverage.
        Use as a reference lookup before calling get_mp_investverte_esg_view_company for detailed ESG scores.
        Consumes 10 API calls per request.
        For country or sector reference lists, use get_mp_investverte_esg_list_countries or list_sectors.
        """
        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        # Base URL for Investverte companies list
        url = f"{EODHD_API_BASE}/mp/investverte/companies?fmt={fmt}"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            # Propagate API error message
            raise ToolError(str(data["error"]))

        try:
            # Expected: list of {"symbol": ..., "name": ...}
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
