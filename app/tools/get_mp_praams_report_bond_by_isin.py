#get_mp_praams_report_bond_by_isin.py

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


def _canon_isin(v: str) -> Optional[str]:
    """Light validation/normalization for ISIN path param."""
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s:
        return None
    return s.upper()


async def _run_praams_report_bond_by_isin(
    isin: str, email: str, is_full: Optional[bool], api_token: Optional[str]
) -> str:
    ci = _canon_isin(isin)
    if ci is None:
        return _err("Invalid 'isin'. It must be a non-empty string (e.g. 'US7593518852').")
    if not email or not isinstance(email, str):
        return _err("Parameter 'email' is required for report notifications.")

    email = email.strip()

    url = f"{EODHD_API_BASE}/mp/praams/reports/bond/{quote_plus(ci)}?1=1"
    url += _q("email", email)
    if is_full is not None:
        url += _q("isFull", str(is_full).lower())
    if api_token:
        url += _q("api_token", api_token)

    data = await make_request(url)
    if data is None:
        return _err("No response from API.")

    try:
        return json.dumps(data, indent=2)
    except Exception:
        return _err("Unexpected response format from API.")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_praams_report_bond_by_isin(
        isin: str,                             # e.g. "US7593518852"
        email: str,                            # email for notifications
        is_full: Optional[bool] = None,        # full or partial report
        api_token: Optional[str] = None,       # per-call override
    ) -> str:
        """
        Marketplace: Praams Multi-Factor Bond Report by ISIN
        GET /api/mp/praams/reports/bond/{isin}

        Generates a comprehensive PDF report with multi-factor analysis
        for a bond identified by its ISIN code.

        Args:
            isin (str): ISIN code of the bond (e.g. 'US7593518852', 'US91282CJN20').
            email (str): Email address for report notifications.
            is_full (bool, optional): True for full report, False for partial.
            api_token (str, optional): Per-call token override; env token used otherwise.

        Notes:
            - Marketplace product: 10 API calls per request.
            - Response is a PDF file download (application/pdf).
            - Coverage: 120,000+ global bonds (corporate and sovereign).
            - Return factors: valuation, performance, analyst view, profitability,
              growth, dividends/coupons.
            - Risk factors: default, volatility, stress-test, selling difficulty,
              country, other risks.
            - Demo ISINs: US7593518852, US91282CJN20.
        """
        return await _run_praams_report_bond_by_isin(
            isin=isin, email=email, is_full=is_full, api_token=api_token
        )

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_praams_report_bond_by_isin(
        isin: str,
        email: str,
        is_full: Optional[bool] = None,
        api_token: Optional[str] = None,
    ) -> str:
        return await _run_praams_report_bond_by_isin(
            isin=isin, email=email, is_full=is_full, api_token=api_token
        )
