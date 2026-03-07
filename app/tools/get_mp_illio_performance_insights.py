#get_mp_illio_performance_insights.py

import json
from typing import Optional
from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations

def _q(key: str, val: Optional[str | int]) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


# Canonical IDs as required by the endpoint
_ALLOWED_IDS = {"SnP500", "DJI", "NDX"}

# Optional convenience mapping to tolerate common variants (case-insensitive)
_CANONICAL_MAP = {
    "SNP500": "SnP500",
    "SNP-500": "SnP500",
    "S&P500": "SnP500",
    "SP500": "SnP500",
    "SPX": "SnP500",
    "DJI": "DJI",
    "DOW": "DJI",
    "NDX": "NDX",
    "NASDAQ-100": "NDX",
    "NASDAQ100": "NDX",
}


def _canon_id(v: str) -> Optional[str]:
    if not isinstance(v, str) or not v.strip():
        return None
    s = v.strip()
    if s in _ALLOWED_IDS:
        return s
    # case-insensitive convenience normalization
    k = s.upper().replace(" ", "")
    return _CANONICAL_MAP.get(k)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_illio_performance_insights(
        id: str,                          # one of {'SnP500','DJI','NDX'} (common aliases accepted)
        fmt: str = "json",                # JSON only (Marketplace returns JSON)
        api_token: Optional[str] = None,  # per-call override (else env EODHD_API_KEY)
    ) -> str:
        """

        [Illio] Retrieve portfolio-level performance attributes for a major US index.
        Covers S&P 500, Dow Jones, and Nasdaq-100. Returns return metrics, attribution,
        and performance breakdown at the index-portfolio level. Consumes 10 API calls per request.
        For market-level performance comparison across constituents, use get_mp_illio_market_insights_performance.
        For risk attributes of the same indices, use mp_illio_risk_insights.

        Args:
          id: 'SnP500' | 'DJI' | 'NDX'  (common aliases like 'SP500', 'SPX', 'NASDAQ100' accepted)
          fmt: 'json' only (kept for symmetry with other tools)
          api_token: override token; otherwise picked from environment by make_request()

        Returns:
          JSON object with performance attributes for the selected index:
            - category (str): category name, e.g. "performance"
            - id (str): index identifier, e.g. "SnP500"
            - attributes (array): list of performance attribute objects, each containing:
                - name (str): attribute name (e.g. "1W Return", "1M Return", "YTD Return")
                - value (float|null): current attribute value
                - details (object|null): additional breakdown or metadata
          On failure returns ToolError.

        Examples:
            "S&P 500 performance insights" → id="SnP500"
            "Nasdaq-100 performance attributes" → id="NDX"

        
        """
        # Validate fmt
        fmt = (fmt or "json").lower()
        if fmt != "json":
            raise ToolError("Only JSON is supported for this endpoint (fmt must be 'json').")

        # Validate/normalize id
        cid = _canon_id(id)
        if cid is None:
            raise ToolError("Invalid 'id'. Allowed: ['SnP500', 'DJI', 'NDX'] (aliases like 'SP500', 'SPX', 'NASDAQ100' accepted).")

        # Build URL
        # Example: /api/mp/illio/categories/performance/SnP500?api_token=...&fmt=json
        url = f"{EODHD_API_BASE}/mp/illio/categories/performance/{cid}?1=1"
        url += _q("fmt", "json")  # explicit for symmetry with other tools

        if api_token:
            url += _q("api_token", api_token)  # otherwise appended by make_request via env

        # Call upstream
        data = await make_request(url)
        if data is None:
            raise ToolError("No response from API.")


        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))
        # Normalize and return
        try:
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected JSON response format from API.")
