#get_upcoming_earnings.py

import json
from typing import Optional, Union, List
from urllib.parse import quote_plus

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)


def _q(key: str, val: Optional[str]) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(val)}"


def _normalize_symbols(symbols: Optional[Union[str, List[str]]]) -> Optional[str]:
    if symbols is None:
        return None
    if isinstance(symbols, str):
        s = symbols.strip()
        return s if s else None
    if isinstance(symbols, list):
        flat = [str(x).strip() for x in symbols if str(x).strip()]
        return ",".join(flat) if flat else None
    return None


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_upcoming_earnings(
        start_date: Optional[str] = None,         # maps to from= (YYYY-MM-DD)
        end_date: Optional[str] = None,           # maps to to=   (YYYY-MM-DD)
        symbols: Optional[Union[str, List[str]]] = None,  # 'AAPL.US' or ['AAPL.US','MSFT.US']
        fmt: Optional[str] = "json",              # 'json' or 'csv' (docs default csv)
        api_token: Optional[str] = None,          # per-call override
    ) -> str:
        """
        Upcoming Earnings API (/calendar/earnings)

        If 'symbols' is provided, API ignores 'from'/'to' (per docs).
        Otherwise, optional date window defaults server-side to [today, today+7d].
        """
        sym_param = _normalize_symbols(symbols)

        # Build base URL
        url = f"{EODHD_API_BASE}/calendar/earnings?1=1"

        # Add parameters:
        if sym_param:
            url += _q("symbols", sym_param)
            # Per spec: when symbols provided, 'from'/'to' are ignored — so we do NOT append them.
        else:
            url += _q("from", start_date)
            url += _q("to", end_date)

        url += _q("fmt", (fmt or "json").lower())

        if api_token:
            url += _q("api_token", api_token)  # otherwise appended by make_request via env

        # Hit API
        data = await make_request(url)

        # Normalize output
        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            return json.dumps(data, indent=2)
        except Exception:
            if isinstance(data, str):  # e.g., CSV
                return json.dumps({"raw": data}, indent=2)
            return _err("Unexpected response format from API.")
