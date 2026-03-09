#get_mp_praams_report_equity_by_isin.py

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


def _canon_isin(v: str) -> Optional[str]:
    """Light validation/normalization for ISIN path param."""
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s:
        return None
    return s.upper()


async def _run_praams_report_equity_by_isin(
    isin: str, email: str, is_full: Optional[bool], api_token: Optional[str]
) -> str:
    ci = _canon_isin(isin)
    if ci is None:
        raise ToolError("Invalid 'isin'. It must be a non-empty string (e.g. 'US0378331005').")
    if not email or not isinstance(email, str):
        raise ToolError("Parameter 'email' is required for report notifications.")

    email = email.strip()

    url = f"{EODHD_API_BASE}/mp/praams/reports/equity/isin/{quote_plus(ci)}?1=1"
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
    async def get_mp_praams_report_equity_by_isin(
        isin: str,                             # e.g. "US0378331005" (Apple)
        email: str,                            # email for notifications
        is_full: Optional[bool] = None,        # full or partial report
        api_token: Optional[str] = None,       # per-call override
    ) -> str:
        """

        [PRAAMS] Generate a comprehensive multi-factor PDF report for an equity by ISIN code.
        Covers 120,000+ global equities. Report includes valuation, performance, profitability,
        growth, dividends, analyst view, plus risk factors (volatility, stress-test, liquidity,
        country, solvency). Requires an email for delivery notification. Consumes 10 API calls per request.
        For report by ticker, use get_mp_praams_report_equity_by_ticker.
        For JSON risk scoring without PDF, use get_mp_praams_risk_scoring_by_isin.

        Args:
            isin (str): ISIN code (e.g. 'US0378331005' for Apple, 'US88160R1014' for Tesla).
            If you only have a company name or ticker, call resolve_ticker first to obtain the ISIN.
            email (str): Email address for report notifications.
            is_full (bool, optional): True for full report, False for partial.
            api_token (str, optional): Per-call token override; env token used otherwise.


        Returns:
            JSON object with report generation status:
              - success (bool): whether the report request was accepted
              - item (object|null): report metadata if available, including:
                  - reportId (str): unique report identifier
                  - status (str): generation status (e.g. "queued", "processing", "completed")
                  - downloadUrl (str|null): URL to download the PDF when ready
              - message (str): status message (e.g. "Report generation started")
              - errors (array): list of error messages, empty on success
            The actual report is a PDF sent to the provided email address.

        Notes:
            - Marketplace product: 10 API calls per request.
            - Response is a PDF file download (application/pdf).
            - Coverage: 120,000+ global equities (stocks, ETFs).
            - Return factors: valuation, performance, analyst view, profitability,
              growth, dividends/coupons.
            - Risk factors: default, volatility, stress-test, selling difficulty,
              country, other risks.
            - Demo ISINs: US0378331005, US88160R1014, US0231351067.

        Examples:
            "Full Apple equity report by ISIN" → isin="US0378331005", email="user@example.com", is_full=True
            "Tesla equity PDF via ISIN" → isin="US88160R1014", email="user@example.com"

        
        """
        return await _run_praams_report_equity_by_isin(
            isin=isin, email=email, is_full=is_full, api_token=api_token
        )

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_praams_report_equity_by_isin(
        isin: str,
        email: str,
        is_full: Optional[bool] = None,
        api_token: Optional[str] = None,
    ) -> str:
        return await _run_praams_report_equity_by_isin(
            isin=isin, email=email, is_full=is_full, api_token=api_token
        )
