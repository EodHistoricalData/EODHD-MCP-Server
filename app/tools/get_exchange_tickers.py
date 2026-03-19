# get_exchange_tickers.py


from app.api_client import make_request
from app.config import EODHD_API_BASE
from app.response import format_json_response
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

ALLOWED_TYPES = {"common_stock", "preferred_stock", "stock", "etf", "fund"}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_exchange_tickers(
        exchange_code: str,  # e.g., "US", "LSE", "XETRA", "WAR"
        delisted: bool | None = None,  # adds delisted=1 when True
        type: str | None = None,  # one of ALLOWED_TYPES
        fmt: str = "json",  # API supports csv; we default to json
        api_token: str | None = None,  # per-call override
    ) -> list:
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
        if not exchange_code or not isinstance(exchange_code, str):
            raise ToolError("Parameter 'exchange_code' is required (e.g., 'US', 'LSE').")

        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        if type is not None and type not in ALLOWED_TYPES:
            raise ToolError(f"Invalid 'type'. Allowed: {sorted(ALLOWED_TYPES)}")

        url = f"{EODHD_API_BASE}/exchange-symbol-list/{exchange_code}?fmt={fmt}"
        if delisted:
            url += "&delisted=1"
        if type:
            url += f"&type={type}"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return format_json_response(data)
        except Exception:
            raise ToolError("Unexpected response format from API.")
