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
        Marketplace: Index Components (+ historical changes for major indices)
        GET /api/mp/unicornbay/spglobal/comp/{symbol}

        Args:
          - symbol: index ID from the list endpoint (e.g., GSPC.INDX)
          - fmt: 'json' (only)
          - api_token: optional override API token

        Response:
          JSON string (pretty-printed) or {"error": "..."} on failure.
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
