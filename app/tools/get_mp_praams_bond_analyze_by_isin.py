#get_mp_praams_bond_analyze_by_isin.py

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
    """
    Helper to build query parameters safely.
    Skips None/empty, URL-encodes values.
    """
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def _canon_isin(v: str) -> Optional[str]:
    """
    Very light validation/normalization for Praams bond ISIN path param.

    Docs show usage like:
      /api/mp/praams/analyse/bond/US7593518852

    We:
      - Require a non-empty string
      - Strip surrounding whitespace
      - Uppercase alpha characters (ISINs are conventionally uppercase).
    """
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s:
        return None
    return s.upper()


async def _run_praams_bond_by_isin(isin: str, api_token: Optional[str]) -> str:
    """
    Core runner for Praams Bond Risk & Return analysis by ISIN.
    """
    # Validate/normalize ISIN
    ci = _canon_isin(isin)
    if ci is None:
        return _err("Invalid 'isin'. It must be a non-empty string (e.g., 'US7593518852').")

    # Build URL
    # Example: /api/mp/praams/analyse/bond/US7593518852?api_token=...  (JSON only)
    url = f"{EODHD_API_BASE}/mp/praams/analyse/bond/{ci}?1=1"
    if api_token:
        url += _q("api_token", api_token)  # otherwise appended by make_request via env

    # Call upstream
    data = await make_request(url)
    if data is None:
        return _err("No response from API.")

    # Normalize and return
    # The Praams bond API wraps the payload in: {"success": ..., "item": {...}, "errors": [...]}
    # We just pretty-print whatever comes back.
    try:
        return json.dumps(data, indent=2)
    except Exception:
        return _err("Unexpected JSON response format from API.")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_praams_bond_analyze_by_isin(
        isin: str,                       # e.g. 'US7593518852' (demo supports US7593518852, US91282CJN20)
        api_token: Optional[str] = None, # per-call override (else env EODHD_API_KEY)
    ) -> str:
        """
        Marketplace: Praams Bond Risk & Return Analysis by ISIN
        GET /api/mp/praams/analyse/bond/{isin}

        Retrieves Praams' detailed bond analytics for a single instrument,
        identified by its ISIN (e.g., 'US7593518852').

        The response includes, among others:
          - PRAAMS ratio & summarized risk/return assessment
          - Coupon profile (fixed / floating, structure, notes)
          - Credit / solvency, stress test, volatility & liquidity narratives
          - Country and other risk descriptions
          - Profitability, growth & momentum metrics at the issuer level
          - Market view (spreads, yield/price history where available)

        Limits (Marketplace rules):
          - 1 request = 10 API calls
          - 100k calls / 24h, 1k requests / minute
          - Output is JSON only
        """
        return await _run_praams_bond_by_isin(isin=isin, api_token=api_token)

    # Optional alias for convenience/back-compat (shorter name)
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_praams_bond_analyze_by_isin(
        isin: str,
        api_token: Optional[str] = None,
    ) -> str:
        return await _run_praams_bond_by_isin(isin=isin, api_token=api_token)
