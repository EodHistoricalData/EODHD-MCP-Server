#get_exchanges_list.py

import json
from typing import Optional

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_exchanges_list(
        fmt: str = "json",                 # API supports csv too; tool defaults to json
        api_token: Optional[str] = None,   # per-call override (env token otherwise)
    ) -> str:
        """
        Get List of Exchanges (GET /api/exchanges-list/)

        Returns:
            str: JSON array of exchanges, each with fields:
                 Name, Code, OperatingMIC, Country, Currency, CountryISO2, CountryISO3
        """
        if fmt != "json":
            return _err("Only 'json' is supported by this tool.")

        url = f"{EODHD_API_BASE}/exchanges-list/?fmt={fmt}"
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
