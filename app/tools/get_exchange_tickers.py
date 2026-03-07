# get_exchange_tickers.py

import json

from app.api_client import make_request
from app.config import EODHD_API_BASE
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
    ) -> str:
        """
        Get List of Tickers for an Exchange (GET /api/exchange-symbol-list/{EXCHANGE_CODE})

        Notes:
            - By default, API returns tickers active in the last month.
            - For US, you can use 'US' (unified) or specific venues (NYSE, NASDAQ, etc.).
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
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
