# app/tools/get_historical_dividends.py

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
    async def get_historical_dividends(
        ticker: str,  # SYMBOL.EXCHANGE_ID, e.g. "AAPL.US"
        start_date: str | None = None,  # maps to 'from' (YYYY-MM-DD)
        end_date: str | None = None,  # maps to 'to'   (YYYY-MM-DD)
        fmt: str = "json",  # endpoint examples use json; tool gates to json
        api_token: str | None = None,  # per-call override; env token otherwise
    ) -> ResourceResponse:
        """

        Get historical dividend records for a stock, ETF, or fund ticker.
        Returns ex-dividend dates, dividend amounts, and for many major tickers also declaration,
        record, and payment dates. Free access may be limited to roughly 1 year of history,
        while paid plans can return deeper history.
        Use when the user asks about dividend history, ex-dividend dates, payout trends,
        or dividend event details for a specific ticker.
        For upcoming dividend calendar events across symbols or dates, use get_upcoming_dividends.

        Args:
            ticker (str): Symbol in SYMBOL.EXCHANGE format, e.g. 'AAPL.US'.
            start_date (str, optional): 'from' date in YYYY-MM-DD.
            end_date (str, optional): 'to' date in YYYY-MM-DD.
            fmt (str): 'json' only.
            api_token (str, optional): Per-call token override.

        Returns:
            Array of dividend records, each with fields such as:
            - date (str): ex-dividend date
            - declarationDate (str | null): declaration date when available
            - recordDate (str | null): record date when available
            - paymentDate (str | null): payment date when available
            - period (str | null): payout frequency such as 'Quarterly'
            - value (float): adjusted dividend value
            - unadjustedValue (float): unadjusted dividend value
            - currency (str): dividend currency

        Examples:
            "Apple dividend history since 2024" → ticker="AAPL.US", start_date="2024-01-01"
            "Microsoft dividends in 2025" → ticker="MSFT.US", start_date="2025-01-01", end_date="2025-12-31"
            "Latest dividend history for VTI" → ticker="VTI.US"

        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        ticker = sanitize_ticker(ticker)

        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        start_date = coerce_date_param(start_date, "start_date")
        end_date = coerce_date_param(end_date, "end_date")
        validate_date_range(start_date, end_date)

        url = build_url(
            f"div/{ticker}",
            {
                "from": start_date,
                "to": end_date,
                "fmt": fmt,
                "api_token": api_token,
            },
        )

        data = await make_request(url)

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
