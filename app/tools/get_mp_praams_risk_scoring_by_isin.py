#get_mp_praams_risk_scoring_by_isin.py

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
    Very light validation/normalization for Praams ISIN path param.

    Docs show usage like:
      /api/mp/praams/analyse/equity/isin/US88160R1014

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


async def _run_praams_equity_by_isin(isin: str, api_token: Optional[str]) -> str:
    """
    Core runner for Praams Equity Risk & Return Scoring by ISIN.
    """
    # Validate/normalize ISIN
    ci = _canon_isin(isin)
    if ci is None:
        return _err("Invalid 'isin'. It must be a non-empty string (e.g., 'US0378331005').")

    # Build URL
    # Example: /api/mp/praams/analyse/equity/isin/US0378331005?api_token=...  (JSON only)
    url = f"{EODHD_API_BASE}/mp/praams/analyse/equity/isin/{ci}?1=1"
    if api_token:
        url += _q("api_token", api_token)  # otherwise appended by make_request via env

    # Call upstream
    data = await make_request(url)
    if data is None:
        return _err("No response from API.")

    # Normalize and return
    # The Praams API wraps the payload in: {"success": ..., "item": {...}, "errors": [...]}
    # We just pretty-print whatever comes back.
    try:
        return json.dumps(data, indent=2)
    except Exception:
        return _err("Unexpected JSON response format from API.")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_praams_risk_scoring_by_isin(
        isin: str,                       # e.g. 'US0378331005' (demo supports US0378331005, US88160R1014, US0231351067)
        api_token: Optional[str] = None, # per-call override (else env EODHD_API_KEY)
    ) -> str:
        """
        Marketplace: Praams Equity Risk & Return Scoring by ISIN
        GET /api/mp/praams/analyse/equity/isin/{isin}

        Retrieves Praams' equity risk & return scoring for a single asset,
        identified by its ISIN (e.g., 'US0378331005').

        The response includes, among others:
          - PRAAMS Ratio and total risk/return scores
          - Valuation, performance, profitability, growth & momentum
          - Dividend metrics and yields
          - Volatility, stress-testing and liquidity assessment
          - Country risk, solvency, and descriptive risk narratives
          - Analyst view and price targets

        Limits (Marketplace rules):
          - 1 request = 10 API calls
          - 100k calls / 24h, 1k requests / minute
          - Output is JSON only
        """
        return await _run_praams_equity_by_isin(isin=isin, api_token=api_token)

    # Optional alias for convenience/back-compat (shorter name)
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_praams_risk_scoring_by_isin(
        isin: str,
        api_token: Optional[str] = None,
    ) -> str:
        return await _run_praams_equity_by_isin(isin=isin, api_token=api_token)
