# get_mp_investverte_esg_list_countries.py

import json

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_investverte_esg_list_countries(
        fmt: str | None = "json",
        api_token: str | None = None,  # per-call override
    ) -> str:
        """

        [InvestVerte] List all countries available in the ESG dataset.
        Returns an array of country_code/country_descr pairs for every country with ESG coverage.
        Use as a reference lookup before calling get_mp_investverte_esg_view_country for detailed ESG scores.
        Consumes 10 API calls per request.
        For company or sector reference lists, use get_mp_investverte_esg_list_companies or list_sectors.


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

        Examples:
            "List all ESG countries" → (no params needed)
            "Which countries have ESG ratings?" → (no params needed)

        
        """
        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        # Base URL for Investverte countries list
        url = f"{EODHD_API_BASE}/mp/investverte/countries?fmt={fmt}"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            # Propagate API error message
            raise ToolError(str(data["error"]))

        try:
            # Expected: list of {"country_code": ..., "country_descr": ...}
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
