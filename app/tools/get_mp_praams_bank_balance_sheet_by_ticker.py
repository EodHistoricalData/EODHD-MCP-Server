# app/tools/get_mp_praams_bank_balance_sheet_by_ticker.py

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


async def _run_praams_balance_sheet_by_ticker(
    ticker: str,
    api_token: str | None,
) -> list:
    """
    Core runner for Praams Bank Balance Sheet by ticker.


        Examples:
            "JPMorgan balance sheet" → ticker="JPM"
            "HSBC bank balance sheet" → ticker="HSBA.LSE"

    """
    # Validate/normalize ticker
    ct = _canon_ticker(ticker)

    # Build URL
    # Example:
    #   /api/mp/praams/bank/balance_sheet/ticker/JPM?api_token=...  (JSON only)
    url = build_url(f"mp/praams/bank/balance_sheet/ticker/{ct}", {"api_token": api_token})

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
    async def get_mp_praams_bank_balance_sheet_by_ticker(
        ticker: str,  # e.g. 'JPM', 'BAC', 'WFC'
        api_token: str | None = None,  # per-call override (else env EODHD_API_KEY)
    ) -> ResourceResponse:
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
