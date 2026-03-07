#get_mp_indices_list.py

import json
from typing import Optional
from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations

def _q(key: str, val: Optional[str]) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_indices_list(
        fmt: str = "json",                 # API returns JSON; expose for symmetry
        api_token: Optional[str] = None,   # per-call override (else env EODHD_API_KEY)
    ) -> str:
        """
        [Marketplace] List all available S&P and Dow Jones indices with end-of-day details.
        Use when asked to browse or enumerate major stock market indices, or to find an index
        symbol before fetching its components with mp_index_components.
        Covers 100+ indices including S&P 500, Dow Jones, and sector indices.
        For components/constituents of a specific index, use mp_index_components.
        Consumes 10 API calls per request.

        Args:
          - fmt: 'json' (default). (CSV is not documented; keep JSON only.)
          - api_token: optional override API token


        Examples:
            "show all S&P and Dow Jones indices" → (no params)
            "list available market indices with details" → (no params)

        """
        fmt = (fmt or "json").lower()
        if fmt != "json":
            raise ToolError("Only JSON is supported for this endpoint.")

        url = f"{EODHD_API_BASE}/mp/unicornbay/spglobal/list?1=1"
        url += _q("fmt", "json")
        if api_token:
            url += _q("api_token", api_token)  # otherwise appended by make_request

        data = await make_request(url)
        if data is None:
            raise ToolError("No response from API.")

        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))
        try:
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected JSON response format from API.")
