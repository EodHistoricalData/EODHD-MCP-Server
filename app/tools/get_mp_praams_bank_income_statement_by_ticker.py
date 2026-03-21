# get_mp_praams_bank_income_statement_by_ticker.py

from app.api_client import make_request
from app.input_formatter import build_url
from app.response_formatter import format_json_response
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def _canon_ticker(v: str) -> str | None:
    """
    Very light validation/normalization for Praams bank ticker path param.

    Docs show usage like:
      /api/mp/praams/bank/income_statement/ticker/JPM

    We:
      - Require a non-empty string
      - Strip surrounding whitespace
      - Preserve original casing (bank tickers can contain dots, etc.).
    """
    if not isinstance(v, str):
        return None
    s = v.strip()
    return s or None


async def _run_praams_bank_income_statement_by_ticker(
    ticker: str,
    api_token: str | None,
) -> list:
    """
    Core runner for Praams Bank Income Statement by ticker.


        Examples:
            "JPMorgan income statement" → ticker="JPM"
            "HSBC bank income financials" → ticker="HSBA.LSE"

    """
    # Validate/normalize ticker
    ct = _canon_ticker(ticker)
    if ct is None:
        raise ToolError("Invalid 'ticker'. It must be a non-empty string (e.g., 'JPM').")

    # Build URL
    # Example:
    #   /api/mp/praams/bank/income_statement/ticker/JPM?api_token=...  (JSON only)
    url = build_url(f"mp/praams/bank/income_statement/ticker/{ct}", {"api_token": api_token})

    # Call upstream
    data = await make_request(url)

    # Normalize and return
    # The API responds with:
    #   {"success": ..., "items": [...], "message": "...", "errors": [...]}
    # We just pretty-print whatever comes back.
    try:
        return format_json_response(data)
    except Exception:
        raise ToolError("Unexpected JSON response format from API.")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_praams_bank_income_statement_by_ticker(
        ticker: str,  # e.g. 'JPM', 'BAC', 'WFC'
        api_token: str | None = None,  # per-call override (else env EODHD_API_KEY)
    ) -> list:
        """

        [PRAAMS] Retrieve bank-specific income statement time series by ticker symbol.
        Returns annual and quarterly data: core revenue, net interest income, fee & commission income,
        RIBPT, non-recurring income, IBPT, and provisioning. Tailored for banking sector analysis.
        Consumes 10 API calls per request.
        For lookup by ISIN, use get_mp_praams_bank_income_statement_by_isin.
        For bank balance sheet data, use get_mp_praams_bank_balance_sheet_by_ticker.

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
        return await _run_praams_bank_income_statement_by_ticker(
            ticker=ticker,
            api_token=api_token,
        )
