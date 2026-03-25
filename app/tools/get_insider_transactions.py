# app/tools/get_insider_transactions.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, coerce_date_param, sanitize_ticker, validate_date_range
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_insider_transactions(
        start_date: str | None = None,  # maps to 'from' (YYYY-MM-DD)
        end_date: str | None = None,  # maps to 'to'   (YYYY-MM-DD)
        limit: int = 100,  # 1..1000, default 100
        symbol: str | None = None,  # maps to 'code' (e.g., 'AAPL' or 'AAPL.US')
        fmt: str = "json",  # API returns json; we gate to json
        api_token: str | None = None,  # per-call token override
    ) -> ResourceResponse:
        """

        Fetch SEC Form 4 insider trading transactions -- purchases and sales by company officers, directors, and major shareholders.
        Returns transaction date, insider name, title, transaction type (P=Purchase, S=Sale), shares, and value.
        Filter by ticker symbol and/or date range. Each request consumes 10 API calls.
        Use when the user asks about insider buying/selling activity, executive stock transactions, or Form 4 filings.

        Args:
            start_date (str, optional): 'from' in YYYY-MM-DD. Defaults to ~1 year ago by API if omitted.
            end_date (str, optional):   'to'   in YYYY-MM-DD. Defaults to today by API if omitted.
            limit (int): Number of entries to return, 1..1000. Default 100.
            symbol (str, optional): Filter by ticker (API param 'code'), e.g. 'AAPL' or 'AAPL.US'.
            fmt (str): Only 'json' is supported by this tool.
            api_token (str, optional): Per-call token; env token used if omitted.

        Returns:
            Object with:
            - code (str): ticker symbol
            - transactions (list): array of transactions, each with:
              - date (str): transaction date
              - ownerName (str): insider name
              - transactionType (str): 'P' (Purchase) or 'S' (Sale)
              - sharesTraded (int): number of shares traded
              - pricePerShare (float|null): price per share
              - sharesOwned (int): total shares owned after transaction

        Notes:
            • Each request consumes 10 API calls (per docs).
            • Transaction codes in results include 'P' (Purchase) and 'S' (Sale).

        Examples:
            "Apple insider trades this year" → symbol="AAPL.US", start_date="2026-01-01", end_date="2026-03-06"
            "Recent insider transactions, top 50" → limit=50
            "Tesla insider buys and sells in Feb 2026" → symbol="TSLA.US", start_date="2026-02-01", end_date="2026-02-28"

        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        # --- Validate inputs ---
        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        if not isinstance(limit, int) or not (1 <= limit <= 1000):
            raise ToolError("'limit' must be an integer between 1 and 1000.")

        if isinstance(symbol, str) and not symbol.strip():
            symbol = None
        elif symbol is not None:
            symbol = sanitize_ticker(symbol, param_name="symbol")

        start_date = coerce_date_param(start_date, "start_date")
        end_date = coerce_date_param(end_date, "end_date")
        validate_date_range(start_date, end_date)

        # --- Build URL per docs ---
        # Example:
        # /api/insider-transactions?fmt=json&limit=100&from=2024-03-01&to=2024-03-02&code=AAPL.US
        url = build_url(
            "insider-transactions",
            {
                "fmt": fmt,
                "limit": limit,
                "from": start_date,
                "to": end_date,
                "code": symbol,
                "api_token": api_token,
            },
        )

        # --- Request ---
        data = await make_request(url)

        # --- Normalize / return ---
        return format_json_response(data)
