# app/tools/get_mp_index_components.py

import logging
from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, sanitize_ticker
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_index_components(
        symbol: str,  # e.g., "GSPC.INDX" from mp_indices_list
        fmt: str = "json",  # JSON only (per docs)
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
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
        symbol = sanitize_ticker(symbol, param_name="symbol")

        fmt = (fmt or "json").lower()
        if fmt != "json":
            raise ToolError("Only JSON is supported for this endpoint.")

        # Build URL - symbol is in the path
        path_symbol = quote_plus(symbol)
        url = build_url(f"mp/unicornbay/spglobal/comp/{path_symbol}", {"fmt": "json", "api_token": api_token})

        data = await make_request(url)

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected JSON response format from API.") from e
