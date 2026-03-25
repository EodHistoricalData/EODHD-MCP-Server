# app/tools/get_mp_praams_risk_scoring_by_isin.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def _canon_isin(v: str) -> str | None:
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


async def _run_praams_equity_by_isin(isin: str, api_token: str | None) -> list:
    """
    Core runner for Praams Equity Risk & Return Scoring by ISIN.


        Examples:
            "Apple risk score by ISIN" → isin="US0378331005"
            "Tesla risk scoring via ISIN" → isin="US88160R1014"

    """
    # Validate/normalize ISIN
    ci = _canon_isin(isin)
    if ci is None:
        raise ToolError("Invalid 'isin'. It must be a non-empty string (e.g., 'US0378331005').")

    # Build URL
    # Example: /api/mp/praams/analyse/equity/isin/US0378331005?api_token=...  (JSON only)
    url = build_url(f"mp/praams/analyse/equity/isin/{ci}", {"api_token": api_token})

    # Call upstream
    data = await make_request(url)
    # Normalize and return
    # The Praams API wraps the payload in: {"success": ..., "item": {...}, "errors": [...]}
    # We just pretty-print whatever comes back.
    try:
        return format_json_response(data)
    except ToolError:
        raise
    except Exception as e:
        logger.debug("API response parse error", exc_info=True)
        raise ToolError("Unexpected JSON response format from API.") from e


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_praams_risk_scoring_by_isin(
        isin: str,  # e.g. 'US0378331005' (demo supports US0378331005, US88160R1014, US0231351067)
        api_token: str | None = None,  # per-call override (else env EODHD_API_KEY)
    ) -> ResourceResponse:
        """

        [PRAAMS] Get risk scores and risk-return decomposition for an equity identified by ISIN code.
        Returns overall PRAAMS ratio (1-7), sub-scores for valuation, performance, profitability,
        growth, dividends, volatility, liquidity, stress-manual, country risk, and solvency.
        Use when assessing investment risk and you have the ISIN. Consumes 10 API calls per request.
        For lookup by ticker instead of ISIN, use get_mp_praams_risk_scoring_by_ticker.
        For a full PDF report, use get_mp_praams_report_equity_by_isin.

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
                - stressTest (object): stress-manual scenarios and score
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
        return await _run_praams_equity_by_isin(isin=isin, api_token=api_token)
