# app/tools/get_exchange_tickers.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, sanitize_exchange
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"common_stock", "preferred_stock", "stock", "etf", "fund"}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_exchange_tickers(
        exchange_code: str,  # e.g., "US", "LSE", "XETRA", "WAR"
        delisted: bool | None = None,  # adds delisted=1 when True
        type: str | None = None,  # one of ALLOWED_TYPES
        fmt: str = "json",  # API supports csv; we default to json
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        List all tickers (symbols) available on a given exchange. Use when the user needs to
        enumerate stocks, ETFs, or funds on an exchange, or check if a specific instrument
        is listed there.

        Covers common stocks, preferred stocks, ETFs, and funds. By default returns tickers
        active in the last month. Supports delisted tickers via the delisted flag. For US
        markets, use 'US' (unified) or specific venues like NYSE, NASDAQ.

        For the list of all exchanges, use get_exchanges_list.
        For exchange metadata and trading hours, use get_exchange_details.

        Returns:
            Array of ticker objects, each with:
            - Code (str): ticker symbol
            - Name (str): instrument name
            - Country (str): country of listing
            - Exchange (str): exchange code
            - Currency (str): trading currency
            - Type (str): instrument type (e.g. "Common Stock", "ETF")
            - Isin (str|null): ISIN code, if available

        Examples:
            "All tickers on London Stock Exchange" → get_exchange_tickers(exchange_code="LSE")
            "Show me delisted US stocks" → get_exchange_tickers(exchange_code="US", delisted=True)
            "ETFs trading on XETRA" → get_exchange_tickers(exchange_code="XETRA", type="etf")
        """
        exchange_code = sanitize_exchange(exchange_code)

        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        if type is not None and type not in ALLOWED_TYPES:
            raise ToolError(f"Invalid 'type'. Allowed: {sorted(ALLOWED_TYPES)}")

        url = build_url(
            f"exchange-symbol-list/{exchange_code}",
            {
                "fmt": fmt,
                "delisted": 1 if delisted else None,
                "type": type,
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
