# app/tools/get_mp_praams_risk_scoring_by_ticker.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, sanitize_ticker
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def _canon_ticker(v: str) -> str:
    return sanitize_ticker(v)


async def _run_praams_equity_by_ticker(ticker: str, api_token: str | None) -> list:
    """
    Core runner for Praams Equity Risk & Return Scoring by ticker.


        Examples:
            "Apple risk score" → ticker="AAPL"
            "Tesla risk and return scoring" → ticker="TSLA"

    """
    # Validate/normalize ticker
    ct = _canon_ticker(ticker)

    # Build URL
    # Example: /api/mp/praams/analyse/equity/ticker/AAPL?api_token=...  (JSON only)
    url = build_url(f"mp/praams/analyse/equity/ticker/{ct}", {"api_token": api_token})

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
    async def get_mp_praams_risk_scoring_by_ticker(
        ticker: str,  # e.g. 'AAPL' (demo supports AAPL, TSLA, AMZN)
        api_token: str | None = None,  # per-call override (else env EODHD_API_KEY)
    ) -> ResourceResponse:
        """

        [PRAAMS] Get risk scores and risk-return decomposition for an equity identified by ticker symbol.
        Returns overall PRAAMS ratio (1-7), sub-scores for valuation, performance, profitability,
        growth, dividends, volatility, liquidity, stress-manual, country risk, and solvency.
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
        return await _run_praams_equity_by_ticker(ticker=ticker, api_token=api_token)
