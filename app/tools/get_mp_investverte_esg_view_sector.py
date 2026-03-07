#get_mp_investverte_esg_view_sector.py

import json
from typing import Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_investverte_esg_view_sector(
        symbol: str,                    # e.g., "Airlines"
        fmt: Optional[str] = "json",
        api_token: Optional[str] = None,  # per-call override
    ) -> str:
        """

        [InvestVerte] Get detailed ESG time-series data for a specific sector by name.
        Returns ESG values mapped by industry/sub-sector across all available year-frequency
        combinations (e.g., "2015-FY", "2021-Q3"). Consumes 10 API calls per request.
        Use get_mp_investverte_esg_list_sectors first to discover available sector names.
        For company-level ESG, use get_mp_investverte_esg_view_company.
        For country-level ESG, use get_mp_investverte_esg_view_country.


        Returns:
            A JSON-formatted string with a sector ESG object:
            {
              "find": true,
              "industry": {
                "Airlines": [<ESG values per year>],
                "Transportation": [<ESG values per year>]
              },
              "years": ["2015-FY", "2015-Q1", ...]
            }
            Fields:
              - find (bool): whether the sector was found
              - industry (object): map of industry/sector names to arrays of ESG
                values aligned with the "years" axis
              - years (array of str): time axis labels in "YYYY-frequency" format

        Notes:
            - The 'industry' section contains sector/industry names mapped
              to ESG values over the 'years' axis.
            - Rate limits (Marketplace product):
                * 100,000 API calls per 24 hours
                * 1,000 API requests per minute
                * 1 API request = 10 API calls

        Examples:
            "Airlines sector ESG data" → symbol="Airlines"
            "Aerospace & Defense ESG ratings" → symbol="Aerospace & Defense"

        
        """
        if not symbol or not isinstance(symbol, str):
            raise ToolError("Parameter 'symbol' is required and must be a non-empty string (e.g., 'Airlines').")

        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        # Base URL for Investverte sector view endpoint
        url = f"{EODHD_API_BASE}/mp/investverte/sector/{symbol}?fmt={fmt}"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            # Propagate API error message
            raise ToolError(str(data["error"]))

        try:
            # Expected: dict with keys like "find", "industry", "years"
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
