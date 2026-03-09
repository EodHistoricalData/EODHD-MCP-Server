#get_mp_praams_risk_scoring_by_ticker.py

import json
from typing import Optional
from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations

def _q(key: str, val: Optional[str | int]) -> str:
    """
    Helper to build query parameters safely.
    Skips None/empty, URL-encodes values.
    """
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def _canon_ticker(v: str) -> Optional[str]:
    """
    Very light validation/normalization for Praams ticker path param.

    Docs show usage like:
      /api/mp/praams/analyse/equity/ticker/AAPL

    We:
      - Require a non-empty string
      - Strip surrounding whitespace
      - Preserve original casing (tickers can be case-sensitive / contain dots, etc.).
    """
    if not isinstance(v, str):
        return None
    s = v.strip()
    return s or None


async def _run_praams_equity_by_ticker(ticker: str, api_token: Optional[str]) -> str:
    """
    Core runner for Praams Equity Risk & Return Scoring by ticker.


        Examples:
            "Apple risk score" → ticker="AAPL"
            "Tesla risk and return scoring" → ticker="TSLA"

    """
    # Validate/normalize ticker
    ct = _canon_ticker(ticker)
    if ct is None:
        raise ToolError("Invalid 'ticker'. It must be a non-empty string (e.g., 'AAPL').")

    # Build URL
    # Example: /api/mp/praams/analyse/equity/ticker/AAPL?api_token=...  (JSON only)
    url = f"{EODHD_API_BASE}/mp/praams/analyse/equity/ticker/{ct}?1=1"
    if api_token:
        url += _q("api_token", api_token)  # otherwise appended by make_request via env

    # Call upstream
    data = await make_request(url)
    if data is None:
        raise ToolError("No response from API.")


    if isinstance(data, dict) and data.get("error"):
        raise ToolError(str(data["error"]))
    # Normalize and return
    # The Praams API wraps the payload in: {"success": ..., "item": {...}, "errors": [...]}
    # We just pretty-print whatever comes back.
    try:
        return json.dumps(data, indent=2)
    except Exception:
        raise ToolError("Unexpected JSON response format from API.")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_praams_risk_scoring_by_ticker(
        ticker: str,                      # e.g. 'AAPL' (demo supports AAPL, TSLA, AMZN)
        api_token: Optional[str] = None,  # per-call override (else env EODHD_API_KEY)
    ) -> str:
        """

        [PRAAMS] Get risk scores and risk-return decomposition for an equity identified by ticker symbol.
        Returns overall PRAAMS ratio (1-7), sub-scores for valuation, performance, profitability,
        growth, dividends, volatility, liquidity, stress-test, country risk, and solvency.
        If you only have a company name or ISIN, call resolve_ticker first.
        Use when assessing investment risk for a specific stock or ETF. Consumes 10 API calls per request.
        For lookup by ISIN instead of ticker, use get_mp_praams_risk_scoring_by_isin.
        For a full PDF report, use get_mp_praams_report_equity_by_ticker.

        Returns:
          JSON object with Praams envelope:
            - success (bool): whether the request succeeded
            - item (object): equity analysis payload containing:
                - praamsRatio (float): overall PRAAMS score
                - totalReturnScore (int): aggregate return score (1-7 scale)
                - totalRiskScore (int): aggregate risk score (1-7 scale)
                - valuation (object): valuation metrics and score
                - performance (object): performance metrics and score
                - profitability (object): profitability metrics and score
                - growthMomentum (object): growth & momentum metrics and score
                - dividends (object): dividend yield, payout ratio, score
                - analystView (object): consensus target price, recommendations, score
                - volatility (object): historical volatility, VaR, score
                - stressTest (object): stress-test scenarios and score
                - liquidity (object): trading volume, bid-ask spread, score
                - countryRisk (object): country-level risk assessment and score
                - solvency (object): debt ratios, interest coverage, score
                - descriptions (object|null): narrative risk/return explanations
            - errors (array): list of error messages, empty on success
            - message (str): status message

        Limits (Marketplace rules):
          - 1 request = 10 API calls
          - 100k calls / 24h, 1k requests / minute
          - Output is JSON only

        """
        return await _run_praams_equity_by_ticker(ticker=ticker, api_token=api_token)

    # Optional alias for convenience/back-compat (shorter name)
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_praams_risk_scoring_by_ticker(
        ticker: str,
        api_token: Optional[str] = None,
    ) -> str:
        return await _run_praams_equity_by_ticker(ticker=ticker, api_token=api_token)
