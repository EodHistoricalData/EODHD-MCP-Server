# get_mp_praams_bank_balance_sheet_by_ticker.py

import json
from urllib.parse import quote_plus

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def _q(key: str, val: str | int | None) -> str:
    """
    Helper to build query parameters safely.
    Skips None/empty, URL-encodes values.
    """
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def _canon_ticker(v: str) -> str | None:
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
    api_token: str | None,
) -> str:
    """
    Core runner for Praams Bank Balance Sheet by ticker.


        Examples:
            "JPMorgan balance sheet" → ticker="JPM"
            "HSBC bank balance sheet" → ticker="HSBA.LSE"

    """
    # Validate/normalize ticker
    ct = _canon_ticker(ticker)
    if ct is None:
        raise ToolError("Invalid 'ticker'. It must be a non-empty string (e.g., 'JPM').")

    # Build URL
    # Example:
    #   /api/mp/praams/bank/balance_sheet/ticker/JPM?api_token=...  (JSON only)
    url = f"{EODHD_API_BASE}/mp/praams/bank/balance_sheet/ticker/{ct}?1=1"
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
    async def get_mp_praams_bank_balance_sheet_by_ticker(
        ticker: str,  # e.g. 'JPM', 'BAC', 'WFC'
        api_token: str | None = None,  # per-call override (else env EODHD_API_KEY)
    ) -> str:
        """

        [PRAAMS] Retrieve bank-specific balance sheet time series by ticker symbol.
        Returns annual and quarterly data: loans, cash, deposits, securities REPO, investment portfolio,
        debt, total assets/equity, interest-earning assets, and interest-bearing liabilities.
        Tailored for banking sector analysis. Consumes 10 API calls per request.
        For lookup by ISIN, use get_mp_praams_bank_balance_sheet_by_isin.
        For bank income statement data, use get_mp_praams_bank_income_statement_by_ticker.

        Returns:
          JSON object with Praams envelope:
            - success (bool): whether the request succeeded
            - items (array): time-series of balance sheet entries, each containing:
                - period (str): reporting period (e.g. "2023-Q4", "2023-FY")
                - loansGross (float|null): gross loans
                - loansProvisions (float|null): loan loss provisions
                - loansNet (float|null): net loans
                - cashEquivalents (float|null): cash & equivalents
                - depositsWithBanks (float|null): deposits with other banks
                - securitiesRepoAssets (float|null): securities REPO assets
                - securitiesRepoLiabilities (float|null): securities REPO liabilities
                - investmentPortfolio (float|null): investment portfolio
                - totalAssets (float|null): total assets
                - totalEquity (float|null): total equity
                - shortTermDebt (float|null): short-term debt
                - longTermDebt (float|null): long-term debt
                - interestEarningAssets (float|null): interest-earning assets
                - interestBearingLiabilities (float|null): interest-bearing liabilities
                - Additional bank-specific balance sheet line items
            - message (str): status message
            - errors (array): list of error messages, empty on success

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
        api_token: str | None = None,
    ) -> str:
        return await _run_praams_balance_sheet_by_ticker(
            ticker=ticker,
            api_token=api_token,
        )
