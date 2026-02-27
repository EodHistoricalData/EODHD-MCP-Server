#get_mp_illio_risk_insights.py

import json
from typing import Optional
from urllib.parse import quote_plus

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations

def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)


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
    async def mp_illio_risk_insights(
        id: str,                          # one of {'SnP500','DJI','NDX'} (common aliases accepted)
        fmt: str = "json",                # JSON only (Marketplace returns JSON)
        api_token: Optional[str] = None,  # per-call override (else env EODHD_API_KEY)
    ) -> str:
        """
        Marketplace: illio Risk Insights (v1.0.0)
        GET /api/mp/illio/categories/risk/{id}

        Returns risk attributes for:
          - SnP500 (S&P 500)
          - DJI    (Dow Jones Industrial Average)
          - NDX    (Nasdaq-100)

        Notes & Limits (Marketplace rules):
          - 1 request = 10 API calls
          - 100k calls / 24h, 1k requests / minute
          - Output is JSON

        Args:
          id: 'SnP500' | 'DJI' | 'NDX'  (common aliases like 'SP500', 'SPX', 'NASDAQ100' accepted)
          fmt: 'json' only (kept for symmetry with other tools)
          api_token: override token; otherwise picked from environment by make_request()

        Returns:
          Pretty-printed JSON string or {"error": "..."} on failure.
        """
        # Validate fmt
        fmt = (fmt or "json").lower()
        if fmt != "json":
            return _err("Only JSON is supported for this endpoint (fmt must be 'json').")

        # Validate/normalize id
        cid = _canon_id(id)
        if cid is None:
            return _err("Invalid 'id'. Allowed: ['SnP500', 'DJI', 'NDX'] (aliases like 'SP500', 'SPX', 'NASDAQ100' accepted).")

        # Build URL
        # Example: /api/mp/illio/categories/risk/SnP500?api_token=...&fmt=json
        url = f"{EODHD_API_BASE}/mp/illio/categories/risk/{cid}?1=1"
        url += _q("fmt", "json")  # explicit for symmetry with other tools

        if api_token:
            url += _q("api_token", api_token)  # otherwise appended by make_request via env

        # Call upstream
        data = await make_request(url)
        if data is None:
            return _err("No response from API.")

        # Normalize and return
        try:
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected JSON response format from API.")
