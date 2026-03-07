#get_mp_praams_bank_income_statement_by_isin.py

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


        Examples:
            "JPMorgan income statement by ISIN" → isin="US46625H1005"
            "Bank of America income via ISIN" → isin="US0605051046"

    """
    # Validate/normalize ISIN
    ci = _canon_isin(isin)
    if ci is None:
        raise ToolError(
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
        raise ToolError("No response from API.")


    if isinstance(data, dict) and data.get("error"):
        raise ToolError(str(data["error"]))
    # Normalize and return
    # The API responds with:
    #   {"success": ..., "items": [...], "message": "...", "errors": [...]}
    # We just pretty-print whatever comes back.
    try:
        return json.dumps(data, indent=2)
    except Exception:
        raise ToolError("Unexpected JSON response format from API.")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_praams_bank_income_statement_by_isin(
        isin: str,                       # e.g. 'US46625H1005' (JPM), 'US0605051046' (BAC)
        api_token: Optional[str] = None,  # per-call override (else env EODHD_API_KEY)
    ) -> str:
        """

        [PRAAMS] Retrieve bank-specific income statement time series by ISIN code.
        Returns annual and quarterly data: core revenue, net interest income, fee & commission income,
        RIBPT, non-recurring income, IBPT, and provisioning. Tailored for banking sector analysis.
        Consumes 10 API calls per request.
        For lookup by ticker, use get_mp_praams_bank_income_statement_by_ticker.
        For bank balance sheet data, use get_mp_praams_bank_balance_sheet_by_isin.

        Returns:
          JSON object with Praams envelope:
            - success (bool): whether the request succeeded
            - items (array): time-series of income statement entries, each containing:
                - period (str): reporting period (e.g. "2023-Q4", "2023-FY")
                - coreRevenue (float|null): total core revenue
                - netInterestIncome (float|null): net interest income
                - netFeeCommissionIncome (float|null): net fee & commission income
                - ribpt (float|null): recurring income before provisioning and taxes
                - nonRecurringIncome (float|null): non-recurring income items
                - ibpt (float|null): income before provisioning and taxes
                - provisioning (float|null): loan loss provisions
                - Additional bank-specific income line items
            - message (str): status message
            - errors (array): list of error messages, empty on success

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
