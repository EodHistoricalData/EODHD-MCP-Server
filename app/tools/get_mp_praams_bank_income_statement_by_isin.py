#get_mp_praams_bank_income_statement_by_isin.py

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
    Very light validation/normalization for Praams bank ISIN path param.

    Docs show usage like:
      /api/mp/praams/bank/income_statement/isin/US46625H1005

    We:
      - Require a non-empty string
      - Strip surrounding whitespace
      - Preserve original casing (ISINs are typically uppercase already).
    """
    if not isinstance(v, str):
        return None
    s = v.strip()
    return s or None


async def _run_praams_income_statement_by_isin(
    isin: str,
    api_token: Optional[str],
) -> str:
    """
    Core runner for Praams Bank Income Statement by ISIN.
    """
    # Validate/normalize ISIN
    ci = _canon_isin(isin)
    if ci is None:
        return _err(
            "Invalid 'isin'. It must be a non-empty string "
            "(e.g., 'US46625H1005')."
        )

    # Build URL
    # Example:
    #   /api/mp/praams/bank/income_statement/isin/US46625H1005?api_token=... (JSON only)
    url = f"{EODHD_API_BASE}/mp/praams/bank/income_statement/isin/{ci}?1=1"
    if api_token:
        url += _q("api_token", api_token)  # otherwise appended by make_request via env

    # Call upstream
    data = await make_request(url)
    if data is None:
        return _err("No response from API.")

    # Normalize and return
    # The API responds with:
    #   {"success": ..., "items": [...], "message": "...", "errors": [...]}
    # We just pretty-print whatever comes back.
    try:
        return json.dumps(data, indent=2)
    except Exception:
        return _err("Unexpected JSON response format from API.")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_praams_bank_income_statement_by_isin(
        isin: str,                       # e.g. 'US46625H1005' (JPM), 'US0605051046' (BAC)
        api_token: Optional[str] = None,  # per-call override (else env EODHD_API_KEY)
    ) -> str:
        """
        Marketplace: Praams Bank Income Statement by ISIN
        GET /api/mp/praams/bank/income_statement/isin/{isin}

        Retrieves the income statement data for a bank identified by its ISIN.

        The Praams Bank Financials API provides bank-specific financials using a
        methodology tailored to banking analysis, including (annual and quarterly):

          - Core revenue
          - Net interest income
          - Net fee & commission income
          - RIBPT (Recurring income before provisioning and taxes)
          - Non-recurring income
          - IBPT (Income before provisioning and taxes)
          - Provisioning

        This endpoint returns a time series of income statement entries under "items".

        Limits (Marketplace rules):
          - 1 request = 10 API calls
          - 100k calls / 24h, 1k requests / minute
          - Output is JSON only
        """
        return await _run_praams_income_statement_by_isin(
            isin=isin,
            api_token=api_token,
        )

    # Optional alias for convenience/back-compat (shorter name)
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_praams_bank_income_statement_by_isin(
        isin: str,
        api_token: Optional[str] = None,
    ) -> str:
        return await _run_praams_income_statement_by_isin(
            isin=isin,
            api_token=api_token,
        )
