# app/tools/get_mp_praams_report_equity_by_ticker.py

from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, sanitize_ticker
from app.response_formatter import ResourceResponse, format_binary_response, raise_on_api_error


async def _run_praams_report_equity_by_ticker(
    ticker: str, email: str, is_full: bool | None, api_token: str | None
) -> ResourceResponse:
    ticker = sanitize_ticker(ticker).upper()
    if not email or not isinstance(email, str):
        raise ToolError("Parameter 'email' is required for report notifications.")

    email = email.strip()

    url = build_url(
        f"mp/praams/reports/equity/ticker/{quote_plus(ticker)}",
        {
            "email": email,
            "isFull": str(is_full).lower() if is_full is not None else None,
            "api_token": api_token,
        },
    )

    data = await make_request(url, response_mode="bytes")
    raise_on_api_error(data)

    if not isinstance(data, bytes) or not data:
        raise ToolError("Unexpected response format from API.")
    return format_binary_response(
        data,
        "application/pdf",
        resource_path=f"reports/praams/equity/ticker/{quote_plus(ticker)}.pdf",
    )


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_praams_report_equity_by_ticker(
        ticker: str,  # e.g. "AAPL", "TSLA", "AMZN"
        email: str,  # email for notifications
        is_full: bool | None = None,  # full or partial report
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        [PRAAMS] Generate a comprehensive multi-factor PDF report for an equity by ticker symbol.
        Covers 120,000+ global equities. Report includes valuation, performance, profitability,
        growth, dividends, analyst view, plus risk factors (volatility, stress-manual, liquidity,
        country, solvency). Requires an email for delivery notification. Consumes 10 API calls per request.
        For report by ISIN, use get_mp_praams_report_equity_by_isin.
        For JSON risk scoring without PDF, use get_mp_praams_risk_scoring_by_ticker.

        Args:
            ticker (str): Ticker symbol (e.g. 'AAPL', 'TSLA', 'AMZN').
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
            - Risk factors: default, volatility, stress-manual, selling difficulty,
              country, other risks.
            - Demo tickers: AAPL, TSLA, AMZN.

        Examples:
            "Full Apple equity report" → ticker="AAPL", email="user@example.com", is_full=True
            "Tesla quick equity analysis" → ticker="TSLA", email="user@example.com"


        """
        return await _run_praams_report_equity_by_ticker(
            ticker=ticker, email=email, is_full=is_full, api_token=api_token
        )
