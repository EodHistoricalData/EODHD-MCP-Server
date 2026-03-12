# get_mp_index_components.py

import json
from urllib.parse import quote_plus

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def _q(key: str, val: str | None) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_index_components(
        symbol: str,  # e.g., "GSPC.INDX" from mp_indices_list
        fmt: str = "json",  # JSON only (per docs)
        api_token: str | None = None,  # per-call override
    ) -> str:
        """

        [Marketplace] Get constituent stocks of a specific S&P or Dow Jones index, including
        historical component changes for major indices. Use when asked which stocks are in an
        index, or to track index rebalancing history.
        Requires the index symbol from mp_indices_list (e.g. GSPC.INDX for S&P 500).
        To browse available indices first, use mp_indices_list.
        Consumes 10 API calls per request.

        Args:
          - symbol: index ID from the list endpoint (e.g., GSPC.INDX)
          - fmt: 'json' (only)
          - api_token: optional override API token


        Returns:
            JSON object with:
            - Components (array): Current index constituents, each with:
              - Code (str): Ticker symbol.
              - Exchange (str): Exchange code.
              - Name (str): Company name.
              - Sector (str): GICS sector.
              - Industry (str): GICS industry.
              - Weight (float): Index weight.
            - Historical changes (for major indices): additions/removals over time.

        Examples:
            "what are the S&P 500 components" → symbol="GSPC.INDX"
            "Dow Jones Industrial Average constituents" → symbol="DJI.INDX"
            "S&P 400 MidCap index members" → symbol="SP400.INDX"


        """
        if not (symbol and symbol.strip()):
            raise ToolError("Parameter 'symbol' is required (e.g., 'GSPC.INDX').")

        fmt = (fmt or "json").lower()
        if fmt != "json":
            raise ToolError("Only JSON is supported for this endpoint.")

        # Build URL - symbol is in the path
        path_symbol = quote_plus(symbol.strip())
        url = f"{EODHD_API_BASE}/mp/unicornbay/spglobal/comp/{path_symbol}?1=1"
        url += _q("fmt", "json")
        if api_token:
            url += _q("api_token", api_token)

        data = await make_request(url)
        if data is None:
            raise ToolError("No response from API.")

        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))
        try:
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected JSON response format from API.")
