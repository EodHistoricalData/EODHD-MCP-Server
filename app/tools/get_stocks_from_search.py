#get_stocks_from_search.py

import json
from typing import Optional
from urllib.parse import quote

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


ALLOWED_TYPES = {"all", "stock", "etf", "fund", "bond", "index", "crypto"}

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_stocks_from_search(
        query: str,
        limit: int = 15,                         # per docs: default 15, max 500
        bonds_only: Optional[bool] = None,       # maps to bonds_only=1
        exchange: Optional[str] = None,          # e.g., "US", "PA", "FOREX", "NYSE", "NASDAQ"
        type: Optional[str] = None,              # one of ALLOWED_TYPES
        fmt: str = "json",                       # API supports json here
        api_token: Optional[str] = None,         # per-call override
    ) -> str:
        """
        Search API for Stocks, ETFs, Mutual Funds, Bonds, and Indices.

        Args:
            query (str): Ticker/company/ISIN to search (e.g., 'AAPL', 'Apple Inc', 'US0378331005').
            limit (int): Number of results (default 15, max 500).
            bonds_only (bool, optional): If True, include only bonds (bonds_only=1).
            exchange (str, optional): Exchange code filter (e.g., 'US', 'PA', 'FOREX', 'NYSE').
            type (str, optional): One of {'all','stock','etf','fund','bond','index','crypto'}.
                                  Note: when using 'all', bonds are excluded by default; use type='bond'
                                  or bonds_only=True to include bonds.
            fmt (str): Must be 'json'.
            api_token (str, optional): Per-call API token override (demo does NOT work for Search).

        Returns:
            str: JSON-formatted list of instruments or {"error": "..."}.

        Examples:
            "Find Apple stock" → get_stocks_from_search(query="Apple Inc", type="stock")
            "Search for ISIN US0378331005" → get_stocks_from_search(query="US0378331005")
            "Crypto assets matching ETH" → get_stocks_from_search(query="ETH", type="crypto", limit=10)
        """
        # --- Validate ---
        if not query or not isinstance(query, str):
            raise ToolError("Parameter 'query' is required and must be a string.")
        if fmt != "json":
            raise ToolError("Only 'json' is supported for the Search API.")
        if not isinstance(limit, int) or not (1 <= limit <= 500):
            raise ToolError("'limit' must be an integer between 1 and 500.")
        if type is not None and type not in ALLOWED_TYPES:
            raise ToolError(f"Invalid 'type'. Allowed: {sorted(ALLOWED_TYPES)}")

        # --- Build URL ---
        # Endpoint shape: /api/search/{query_string}?fmt=json&limit=...&bonds_only=1&exchange=...&type=...
        encoded_query = quote(query, safe="")
        url = f"{EODHD_API_BASE}/search/{encoded_query}?fmt={fmt}&limit={limit}"

        if bonds_only:
            url += "&bonds_only=1"
        if exchange:
            url += f"&exchange={quote(str(exchange))}"
        if type:
            url += f"&type={quote(type)}"

        # Per-call token override (note: demo does NOT work for Search)
        if api_token:
            url += f"&api_token={api_token}"

        # --- Request ---
        data = await make_request(url)

        # --- Normalize / return ---
        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
