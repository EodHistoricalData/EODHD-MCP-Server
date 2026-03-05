#get_mp_illio_market_insights_largest_volatility.py

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
    "DOW30": "DJI",
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


async def _run_largest_volatility(id: str, fmt: str, api_token: Optional[str]) -> str:
    """
    Internal runner for Largest Volatility Change chapter.
    """
    # Validate fmt
    fmt = (fmt or "json").lower()
    if fmt != "json":
        raise ToolError("Only JSON is supported for this endpoint (fmt must be 'json').")

    # Validate/normalize id
    cid = _canon_id(id)
    if cid is None:
        raise ToolError(
            "Invalid 'id'. Allowed: ['SnP500', 'DJI', 'NDX'] "
            "(aliases like 'SP500', 'SPX', 'NASDAQ100' accepted)."
        )

    # Build URL
    # Endpoint per docs:
    #   /api/mp/illio/chapters/volume/{id}
    # Example:
    #   /api/mp/illio/chapters/volume/NDX?api_token=...&fmt=json
    url = f"{EODHD_API_BASE}/mp/illio/chapters/volume/{cid}?1=1"
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


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_illio_market_insights_largest_volatility(
        id: str,                          # one of {'SnP500','DJI','NDX'} (common aliases accepted)
        fmt: str = "json",                # JSON only (Marketplace returns JSON)
        api_token: Optional[str] = None,  # per-call override (else env EODHD_API_KEY)
    ) -> str:
        """
        Marketplace: illio Market Insights – Largest Volatility Change (v1.0.0)
        GET /api/mp/illio/chapters/volume/{id}

        Returns chapter: Largest Volatility Change over the past year for:
          - SnP500 (S&P 500)
          - DJI    (Dow Jones Industrial Average)
          - NDX    (Nasdaq-100)

        This insight highlights instruments with the largest increases and decreases
        in 100-day volatility over the past year, including:
          - Overall share of instruments with higher vs lower volatility.
          - Top instruments by volatility increase.
          - Top instruments by volatility decrease.

        Returns:
          JSON object with largest volatility change chapter data:
            - chapter (str): chapter identifier, e.g. "volume"
            - id (str): index identifier, e.g. "NDX"
            - data (object): volatility change analysis, including:
                - summary (object): share of instruments with higher vs lower volatility
                - increasers (array): top instruments by volatility increase, each with
                    ticker, name, volatilityChange (float), currentVolatility (float)
                - decreasers (array): top instruments by volatility decrease, same fields
            - metadata (object|null): date range, lookback period

        Limits (Marketplace rules):
          - 1 request = 10 API calls
          - 100k calls / 24h, 1k requests / minute
          - Output is JSON
        """
        return await _run_largest_volatility(id=id, fmt=fmt, api_token=api_token)

    # Optional alias for convenience/back-compat
    @mcp.tool()
    async def mp_illio_market_insights_largest_volatility(
        id: str,
        fmt: str = "json",
        api_token: Optional[str] = None,
    ) -> str:
        """
        Alias for get_mp_illio_market_insights_largest_volatility.
        """
        return await _run_largest_volatility(id=id, fmt=fmt, api_token=api_token)
