# get_mp_praams_report_bond_by_isin.py

import json
from urllib.parse import quote_plus

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def _q(key: str, val: str | int | None) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def _canon_isin(v: str) -> str | None:
    """Light validation/normalization for ISIN path param."""
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s:
        return None
    return s.upper()


async def _run_praams_report_bond_by_isin(isin: str, email: str, is_full: bool | None, api_token: str | None) -> str:
    ci = _canon_isin(isin)
    if ci is None:
        raise ToolError("Invalid 'isin'. It must be a non-empty string (e.g. 'US7593518852').")
    if not email or not isinstance(email, str):
        raise ToolError("Parameter 'email' is required for report notifications.")

    email = email.strip()

    url = f"{EODHD_API_BASE}/mp/praams/reports/bond/{quote_plus(ci)}?1=1"
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
    async def get_mp_praams_report_bond_by_isin(
        isin: str,  # e.g. "US7593518852"
        email: str,  # email for notifications
        is_full: bool | None = None,  # full or partial report
        api_token: str | None = None,  # per-call override
    ) -> str:
        """

        [PRAAMS] Generate a comprehensive multi-factor PDF report for a bond by ISIN code.
        Covers 120,000+ global bonds (corporate and sovereign). Report includes valuation,
        performance, coupon analysis, profitability, growth, plus risk factors (volatility,
        stress-test, liquidity, country, solvency). Requires an email for delivery notification.
        Consumes 10 API calls per request.
        For JSON bond analysis without PDF, use get_mp_praams_bond_analyze_by_isin.
        For equity PDF reports, use get_mp_praams_report_equity_by_ticker or by_isin.

        Args:
            isin (str): ISIN code of the bond (e.g. 'US7593518852', 'US91282CJN20').
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
            - Coverage: 120,000+ global bonds (corporate and sovereign).
            - Return factors: valuation, performance, analyst view, profitability,
              growth, dividends/coupons.
            - Risk factors: default, volatility, stress-test, selling difficulty,
              country, other risks.
            - Demo ISINs: US7593518852, US91282CJN20.

        Examples:
            "Full bond report for Realty Income" → isin="US7593518852", email="user@example.com", is_full=True
            "US Treasury bond PDF report" → isin="US91282CJN20", email="user@example.com"

        
        """
        return await _run_praams_report_bond_by_isin(isin=isin, email=email, is_full=is_full, api_token=api_token)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_praams_report_bond_by_isin(
        isin: str,
        email: str,
        is_full: bool | None = None,
        api_token: str | None = None,
    ) -> str:
        return await _run_praams_report_bond_by_isin(isin=isin, email=email, is_full=is_full, api_token=api_token)
