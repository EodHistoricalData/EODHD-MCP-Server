# app/tools/get_mp_praams_bank_balance_sheet_by_isin.py

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
    Very light validation/normalization for Praams bank ISIN path param.

    Docs show usage like:
      /api/mp/praams/bank/balance_sheet/isin/US46625H1005

    We:
      - Require a non-empty string
      - Strip surrounding whitespace
      - Uppercase it (ISINs are conventionally uppercase).
    """
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s:
        return None
    return s.upper()


async def _run_praams_balance_sheet_by_isin(
    isin: str,
    api_token: str | None,
) -> list:
    """
    Core runner for Praams Bank Balance Sheet by ISIN.


        Examples:
            "JPMorgan balance sheet by ISIN" → isin="US46625H1005"
            "Bank of America balance sheet ISIN" → isin="US0605051046"

    """
    # Validate/normalize ISIN
    ci = _canon_isin(isin)
    if ci is None:
        raise ToolError("Invalid 'isin'. It must be a non-empty string (e.g., 'US46625H1005').")

    # Build URL
    # Example:
    #   /api/mp/praams/bank/balance_sheet/isin/US46625H1005?api_token=...  (JSON only)
    url = build_url(f"mp/praams/bank/balance_sheet/isin/{ci}", {"api_token": api_token})

    # Call upstream
    data = await make_request(url)
    # Normalize and return
    # The API responds with:
    #   {"success": ..., "items": [...], "message": "...", "errors": [...]}
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
    async def get_mp_praams_bank_balance_sheet_by_isin(
        isin: str,  # e.g. 'US46625H1005', 'US0605051046'
        api_token: str | None = None,  # per-call override (else env EODHD_API_KEY)
    ) -> ResourceResponse:
        """

        [PRAAMS] Retrieve bank-specific balance sheet time series by ISIN code.
        Returns annual and quarterly data: loans, cash, deposits, securities REPO, investment portfolio,
        debt, total assets/equity, interest-earning assets, and interest-bearing liabilities.
        Tailored for banking sector analysis. Consumes 10 API calls per request.
        For lookup by ticker, use get_mp_praams_bank_balance_sheet_by_ticker.
        For bank income statement data, use get_mp_praams_bank_income_statement_by_isin.

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
        return await _run_praams_balance_sheet_by_isin(
            isin=isin,
            api_token=api_token,
        )
