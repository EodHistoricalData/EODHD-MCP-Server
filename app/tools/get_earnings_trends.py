#get_earnings_trends.py

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


def _normalize_symbols(symbols: Union[str, List[str], None]) -> Optional[str]:
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
    async def get_earnings_trends(
        symbols: Union[str, List[str]],      # REQUIRED by API: 'AAPL.US' or ['AAPL.US','MSFT.US']
        fmt: str = "json",                   # Trends are JSON-only (kept for consistency)
        api_token: Optional[str] = None,     # per-call override (else uses env EODHD_API_KEY)
    ) -> str:
        """
        Earnings Trends API (/calendar/trends)
        Notes:
          - 'symbols' is REQUIRED (one or more, comma-separated).
          - Response is JSON only (fmt kept to mirror other tools).
          - Each request consumes ~10 API calls under EODHD's system.
        """
        sym_param = _normalize_symbols(symbols)
        if not sym_param:
            return _err("Parameter 'symbols' is required (e.g., 'AAPL.US' or ['AAPL.US','MSFT.US']).")

        url = f"{EODHD_API_BASE}/calendar/trends?1=1"
        url += _q("symbols", sym_param)
        # JSON-only; still pass fmt for parity with other tools (server ignores non-JSON anyway)
        url += _q("fmt", (fmt or "json").lower())

        if api_token:
            url += _q("api_token", api_token)  # otherwise appended by make_request via env

        data = await make_request(url)

        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            return json.dumps(data, indent=2)
        except Exception:
            # Trends should always be JSON; fallback just in case
            return _err("Unexpected response format from API.")
