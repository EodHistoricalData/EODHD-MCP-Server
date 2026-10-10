# app/tools/get_insider_transactions_form4.py

import logging

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, sanitize_ticker
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)

DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Insider Transactions (SEC Form 4)", readOnlyHint=True))
    async def get_insider_transactions_form4(
        symbol: str,  # US ticker, e.g. "AAPL" or "AAPL.US" (.US suffix optional)
        limit: int = DEFAULT_PAGE_LIMIT,  # maps to 'page[limit]' (1..100)
        offset: int = 0,  # maps to 'page[offset]' (>= 0)
        api_token: str | None = None,  # per-call override; env token otherwise
    ) -> ResourceResponse:
        """

        Get SEC Form 4 insider-trading filings for a US-listed issuer, sourced directly from
        SEC EDGAR. This is the richer V2 ("SEC Form 4") endpoint: each filing exposes
        non-derivative transactions (common stock), derivative transactions (options, RSUs,
        warrants), and the footnotes referenced from each row, with the full SEC transaction
        code set and reporting-owner relationship flags. Costs 10 API calls per request.

        Use when the user asks about insider buying/selling, executive stock transactions, or
        Form 4 filings for a US company and wants full per-filing detail. For a flat, simpler
        list across symbols/dates use the legacy get_insider_transactions tool instead.

        Args:
            symbol (str): US ticker, e.g. 'AAPL' or 'AAPL.US'. Case-insensitive; the .US suffix
                is optional. Form 4 is filed by US-listed issuers only — non-US symbols 404.
            limit (int): Page size, 1..100. Default 20.
            offset (int): Zero-based pagination offset. Default 0.
            api_token (str, optional): Per-call token override.

        Returns:
            Object with:
            - data (array): Form 4 filings (newest filed_at first), each with:
                - accession_number (str): unique SEC filing identifier
                - filed_at (str): submission date (YYYY-MM-DD)
                - period_of_report (str): reporting period (YYYY-MM-DD)
                - non_derivative (array): direct stock transactions, each with reporting_owner_cik,
                  reporting_owner_name, is_director/is_officer/is_ten_percent_owner/is_other,
                  officer_title, security_title, transaction_date, transaction_code,
                  acquired_or_disposed (A/D), shares_amount, price_per_share, shares_owned_after,
                  total_value
                - derivative (array): option/RSU/warrant transactions, adding
                  conversion_or_exercise_price, underlying_security_title, underlying_shares,
                  exercise_date, expiration_date
                - footnotes (array): {footnote_id, text} referenced from transaction rows
            - meta (object): total (int) and page {offset, limit}.
            - links (object): next (str|null) — URL for the next page, null on the last page.

        Notes:
            - 10 API calls per request.
            - Transaction codes follow the SEC Section 16 set (P=purchase, S=sale, A=grant,
              M=exercise/conversion, F=tax withholding, G=gift, etc.).
            - Forward-only pagination: only 'links.next' is exposed. Increment 'offset' (up to
              'meta.total') to reach a specific page.
            - History depth varies by ticker — large caps (AAPL, MSFT, NVDA) reach back many
              years; recently onboarded issuers may expose ~12 months.

        Examples:
            "Apple insider Form 4 filings" → symbol="AAPL.US"
            "Tesla insider transactions, 50 per page" → symbol="TSLA", limit=50
            "Next page of NVDA insider filings" → symbol="NVDA.US", offset=20

        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        symbol = sanitize_ticker(symbol, param_name="symbol")
        if not symbol:
            return format_json_response(
                {"error": "Parameter 'symbol' is required (US ticker, e.g., 'AAPL' or 'AAPL.US')."}
            )

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = DEFAULT_PAGE_LIMIT
        limit = max(1, min(limit, MAX_PAGE_LIMIT))

        try:
            offset = int(offset)
        except (TypeError, ValueError):
            offset = 0
        offset = max(0, offset)

        url = build_url(
            f"sec-filings/{symbol}/form4",
            {
                "page[limit]": limit,
                "page[offset]": offset,
                "api_token": api_token,
            },
        )

        data = await make_request(url)

        return format_json_response(data)
