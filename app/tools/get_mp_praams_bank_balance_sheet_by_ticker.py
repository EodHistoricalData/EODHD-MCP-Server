#get_mp_praams_bank_balance_sheet_by_ticker.py

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


def _canon_ticker(v: str) -> Optional[str]:
    """
    Very light validation/normalization for Praams bank ticker path param.

    Docs show usage like:
      /api/mp/praams/bank/balance_sheet/ticker/JPM

    We:
      - Require a non-empty string
      - Strip surrounding whitespace
      - Preserve original casing (bank tickers can contain dots, etc.).
    """
    if not isinstance(v, str):
        return None
    s = v.strip()
    return s or None


async def _run_praams_balance_sheet_by_ticker(
    ticker: str,
    api_token: Optional[str],
) -> str:
    """
    Core runner for Praams Bank Balance Sheet by ticker.
    """
    # Validate/normalize ticker
    ct = _canon_ticker(ticker)
    if ct is None:
        return _err("Invalid 'ticker'. It must be a non-empty string (e.g., 'JPM').")

    # Build URL
    # Example:
    #   /api/mp/praams/bank/balance_sheet/ticker/JPM?api_token=...  (JSON only)
    url = f"{EODHD_API_BASE}/mp/praams/bank/balance_sheet/ticker/{ct}?1=1"
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
    async def get_mp_praams_bank_balance_sheet_by_ticker(
        ticker: str,                      # e.g. 'JPM', 'BAC', 'WFC'
        api_token: Optional[str] = None,  # per-call override (else env EODHD_API_KEY)
    ) -> str:
        """
        Marketplace: Praams Bank Balance Sheet by Ticker
        GET /api/mp/praams/bank/balance_sheet/ticker/{ticker}

        Retrieves the balance sheet data for a bank identified by its ticker.

        The Praams Bank Financials API provides bank-specific financials using a
        methodology tailored to banking analysis, including (annual and quarterly):

          - Loans (gross, provisions, net)
          - Cash & equivalents
          - Deposits with banks
          - Securities REPO (assets and liabilities)
          - Investment portfolio / long-term investments
          - Trading liabilities, payables, other liabilities
          - Short-term and long-term debt
          - Total assets, total equity, total equity & liabilities
          - Interest-earning assets and interest-bearing liabilities

        This endpoint returns a time series of balance sheet entries under "items".

        Limits (Marketplace rules):
          - 1 request = 10 API calls
          - 100k calls / 24h, 1k requests / minute
          - Output is JSON only
        """
        return await _run_praams_balance_sheet_by_ticker(
            ticker=ticker,
            api_token=api_token,
        )

    # Optional alias for convenience/back-compat (shorter name)
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_praams_bank_balance_sheet_by_ticker(
        ticker: str,
        api_token: Optional[str] = None,
    ) -> str:
        return await _run_praams_balance_sheet_by_ticker(
            ticker=ticker,
            api_token=api_token,
        )
