# get_mp_investverte_esg_list_sectors.py

import json

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_investverte_esg_list_sectors(
        fmt: str | None = "json",
        api_token: str | None = None,  # per-call override
    ) -> str:
        """

        [InvestVerte] List all sectors available in the ESG dataset.
        Returns an array of sector names with ESG coverage (e.g., "Airlines", "Aerospace & Defense").
        Use as a reference lookup before calling get_mp_investverte_esg_view_sector for detailed ESG data.
        Consumes 10 API calls per request.
        For company or country reference lists, use get_mp_investverte_esg_list_companies or list_countries.


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

        Examples:
            "List all ESG sectors" → (no params needed)
            "What sectors have ESG coverage?" → (no params needed)


        """
        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        # Base URL for Investverte sectors list
        url = f"{EODHD_API_BASE}/mp/investverte/sectors?fmt={fmt}"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            # Propagate API error message
            raise ToolError(str(data["error"]))

        try:
            # Expected: list of {"sector": "..."}
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
