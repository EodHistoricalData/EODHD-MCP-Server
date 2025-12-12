#get_live_price_data.py

import json
from typing import Iterable, Optional, Sequence

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations

ALLOWED_FMT = {"json", "csv"}
MAX_EXTRA_TICKERS = 20  # soft limit recommended by docs (15–20)

def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)

def _normalize_symbols(symbols: Optional[Iterable[str]]) -> list[str]:
    if not symbols:
        return []
    out: list[str] = []
    for s in symbols:
        if not s:
            continue
        s = str(s).strip()
        if s:
            out.append(s)
    return out

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_live_price_data(
        ticker: str,
        additional_symbols: Optional[Sequence[str]] = None,
        fmt: str = "json",
        api_token: Optional[str] = None,
    ) -> str:
        """
        Live (Delayed) Stock Prices API

        Args:
            ticker (str): Primary symbol in SYMBOL.EXCHANGE format (e.g., 'AAPL.US').
                          Required and placed in the path, per API spec.
            additional_symbols (Sequence[str], optional): Extra symbols for 's=' query param,
                          comma-separated by the tool (e.g., ['VTI', 'EUR.FOREX']).
                          Docs recommend <= 15–20 total.
            fmt (str): 'json' or 'csv'. Defaults to 'json' for easier client handling.
            api_token (str, optional): Per-call token override. If omitted, env token is used.

        Returns:
            str: JSON string. If fmt='csv' and your `make_request` returns raw text,
                 this tool wraps CSV into {"csv": "..."}; otherwise returns JSON from API.
        """
        # --- Validate inputs ---
        if not ticker or not isinstance(ticker, str):
            return _err("Parameter 'ticker' is required (e.g., 'AAPL.US').")

        if fmt not in ALLOWED_FMT:
            return _err(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        extras = _normalize_symbols(additional_symbols)
        # Prevent duplicates of the primary ticker in 's='
        extras = [s for s in extras if s != ticker]

        if len(extras) > MAX_EXTRA_TICKERS:
            return _err(
                f"Too many symbols in 'additional_symbols'. "
                f"Got {len(extras)}, max recommended is {MAX_EXTRA_TICKERS}."
            )

        # --- Build URL per docs ---
        # Example: /api/real-time/AAPL.US?fmt=json&s=VTI,EUR.FOREX
        url = f"{EODHD_API_BASE}/real-time/{ticker}?fmt={fmt}"
        if extras:
            url += f"&s={','.join(extras)}"

        # Per-call token override. If omitted, make_request will append env token.
        if api_token:
            url += f"&api_token={api_token}"

        # --- Request ---
        data = await make_request(url)

        # --- Normalize errors / outputs ---
        if data is None:
            return _err("No response from API.")

        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        # If make_request always returns JSON (since it calls response.json()),
        # this will succeed for fmt=json. For fmt=csv, consider adapting make_request to return text.
        try:
            return json.dumps(data, indent=2)
        except Exception:
            if isinstance(data, str):  # if you adapted make_request to return text for CSV
                return json.dumps({"csv": data}, indent=2)
            return _err("Unexpected response format from API.")
