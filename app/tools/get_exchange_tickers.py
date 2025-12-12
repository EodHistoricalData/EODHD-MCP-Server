#get_exchange_tickers.py

import json
from typing import Optional

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


ALLOWED_TYPES = {"common_stock", "preferred_stock", "stock", "etf", "fund"}

def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_exchange_tickers(
        exchange_code: str,                # e.g., "US", "LSE", "XETRA", "WAR"
        delisted: Optional[bool] = None,   # adds delisted=1 when True
        type: Optional[str] = None,        # one of ALLOWED_TYPES
        fmt: str = "json",                 # API supports csv; we default to json
        api_token: Optional[str] = None,   # per-call override
    ) -> str:
        """
        Get List of Tickers for an Exchange (GET /api/exchange-symbol-list/{EXCHANGE_CODE})

        Notes:
            - By default, API returns tickers active in the last month.
            - For US, you can use 'US' (unified) or specific venues (NYSE, NASDAQ, etc.).
        """
        if not exchange_code or not isinstance(exchange_code, str):
            return _err("Parameter 'exchange_code' is required (e.g., 'US', 'LSE').")

        if fmt != "json":
            return _err("Only 'json' is supported by this tool.")

        if type is not None and type not in ALLOWED_TYPES:
            return _err(f"Invalid 'type'. Allowed: {sorted(ALLOWED_TYPES)}")

        url = f"{EODHD_API_BASE}/exchange-symbol-list/{exchange_code}?fmt={fmt}"
        if delisted:
            url += "&delisted=1"
        if type:
            url += f"&type={type}"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected response format from API.")
