# app/tools/get_historical_splits.py

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
    async def get_historical_splits(
        ticker: str,  # SYMBOL.EXCHANGE_ID, e.g. "AAPL.US"
        start_date: str | None = None,  # maps to 'from' (YYYY-MM-DD)
        end_date: str | None = None,  # maps to 'to'   (YYYY-MM-DD)
        fmt: str = "json",  # endpoint examples use json; tool gates to json
        api_token: str | None = None,  # per-call override; env token otherwise
    ) -> ResourceResponse:
        """

        Get historical stock split events for a specific ticker.
        Returns split dates and split ratios such as 2-for-1, 4-for-1, or reverse split ratios.
        Use when the user asks about historical splits, reverse splits, or corporate action history
        for a specific stock.
        For upcoming split calendar events across symbols or dates, use get_upcoming_splits.

        Args:
            ticker (str): Symbol in SYMBOL.EXCHANGE format, e.g. 'AAPL.US'.
            start_date (str, optional): 'from' date in YYYY-MM-DD.
            end_date (str, optional): 'to' date in YYYY-MM-DD.
            fmt (str): 'json' only.
            api_token (str, optional): Per-call token override.

        Returns:
            Array of split records, each with:
            - date (str): split effective date
            - split (str): split ratio string such as '4.000000/1.000000'

        Examples:
            "Apple split history since 2000" → ticker="AAPL.US", start_date="2000-01-01"
            "Tesla split history" → ticker="TSLA.US"
            "NVIDIA splits between 2010 and 2025" → ticker="NVDA.US", start_date="2010-01-01", end_date="2025-12-31"

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
            f"splits/{ticker}",
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
