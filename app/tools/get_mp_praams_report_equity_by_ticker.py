#get_mp_praams_report_equity_by_ticker.py

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


async def _run_praams_report_equity_by_ticker(
    ticker: str, email: str, is_full: Optional[bool], api_token: Optional[str]
) -> str:
    if not ticker or not isinstance(ticker, str):
        raise ToolError("Parameter 'ticker' is required (e.g. 'AAPL', 'TSLA').")
    if not email or not isinstance(email, str):
        raise ToolError("Parameter 'email' is required for report notifications.")

    ticker = ticker.strip().upper()
    email = email.strip()

    url = f"{EODHD_API_BASE}/mp/praams/reports/equity/ticker/{quote_plus(ticker)}?1=1"
    url += _q("email", email)
    if is_full is not None:
        url += _q("isFull", str(is_full).lower())
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
        raise ToolError("Unexpected response format from API.")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_praams_report_equity_by_ticker(
        ticker: str,                           # e.g. "AAPL", "TSLA", "AMZN"
        email: str,                            # email for notifications
        is_full: Optional[bool] = None,        # full or partial report
        api_token: Optional[str] = None,       # per-call override
    ) -> str:
        """
        Marketplace: Praams Multi-Factor Equity Report by Ticker
        GET /api/mp/praams/reports/equity/ticker/{ticker}

        Generates a comprehensive PDF report with multi-factor analysis
        for an equity identified by its ticker symbol.

        Args:
            ticker (str): Ticker symbol (e.g. 'AAPL', 'TSLA', 'AMZN').
            email (str): Email address for report notifications.
            is_full (bool, optional): True for full report, False for partial.
            api_token (str, optional): Per-call token override; env token used otherwise.

        Notes:
            - Marketplace product: 10 API calls per request.
            - Response is a PDF file download (application/pdf).
            - Coverage: 120,000+ global equities (stocks, ETFs).
            - Return factors: valuation, performance, analyst view, profitability,
              growth, dividends/coupons.
            - Risk factors: default, volatility, stress-test, selling difficulty,
              country, other risks.
            - Demo tickers: AAPL, TSLA, AMZN.

        Examples:
            "Full Apple equity report" → ticker="AAPL", email="user@example.com", is_full=True
            "Tesla quick equity analysis" → ticker="TSLA", email="user@example.com"
        """
        return await _run_praams_report_equity_by_ticker(
            ticker=ticker, email=email, is_full=is_full, api_token=api_token
        )

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_praams_report_equity_by_ticker(
        ticker: str,
        email: str,
        is_full: Optional[bool] = None,
        api_token: Optional[str] = None,
    ) -> str:
        """
        Alias for get_mp_praams_report_equity_by_ticker.

        Examples:
            "Amazon full equity PDF report" → ticker="AMZN", email="user@example.com", is_full=True
            "Siemens equity report" → ticker="SIE.XETRA", email="user@example.com"
        """
        return await _run_praams_report_equity_by_ticker(
            ticker=ticker, email=email, is_full=is_full, api_token=api_token
        )
