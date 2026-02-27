#get_us_tick_data.py
import json
from typing import Optional, Union

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


ALLOWED_FMT = {"json", "csv"}

def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)

def _to_int(name: str, v: Union[int, str, None]) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.isdigit():
        return int(v)
    raise ValueError(f"'{name}' must be an integer UNIX timestamp in seconds (UTC).")

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_us_tick_data(
        ticker: str,                         # maps to s=
        from_timestamp: Union[int, str],     # UNIX seconds (UTC)
        to_timestamp: Union[int, str],       # UNIX seconds (UTC)
        limit: int = 1000,                   # max number of ticks returned
        fmt: str = "json",                   # 'json' | 'csv'
        api_token: Optional[str] = None,     # per-call override
    ) -> str:
        """
        US Stock Market Tick Data API (GET /api/ticks)
        Returns granular trade ticks for US equities across all venues.

        Args:
            ticker (str): e.g., 'AAPL' or 'AAPL.US' (US-only).
            from_timestamp (int|str): Start UNIX time (seconds, UTC).
            to_timestamp   (int|str): End   UNIX time (seconds, UTC).
            limit (int): Max ticks to return. Example in docs uses 5. Default 1000.
            fmt (str): 'json' (default) or 'csv'.
            api_token (str, optional): Per-call token override; env token used otherwise.

        Notes:
            • Endpoint shape:
              /api/ticks/?s=AAPL&from=1694455200&to=1694541600&limit=5&fmt=json
            • Each request costs 10 API calls (any history depth).
            • Response fields (arrays): mkt, price, seq, shares, sl, sub_mkt, ts (ms).
        """
        # --- Validate inputs ---
        if not ticker or not isinstance(ticker, str):
            return _err("Parameter 'ticker' is required (e.g., 'AAPL' or 'AAPL.US').")

        if fmt not in ALLOWED_FMT:
            return _err(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        try:
            f_ts = _to_int("from_timestamp", from_timestamp)
            t_ts = _to_int("to_timestamp", to_timestamp)
        except ValueError as ve:
            return _err(str(ve))

        if f_ts is None or t_ts is None:
            return _err("'from_timestamp' and 'to_timestamp' are required (UNIX seconds).")
        if f_ts < 0 or t_ts < 0:
            return _err("Timestamps must be non-negative UNIX seconds.")
        if f_ts > t_ts:
            return _err("'from_timestamp' cannot be greater than 'to_timestamp'.")

        if not isinstance(limit, int) or limit <= 0:
            return _err("'limit' must be a positive integer.")

        # --- Build URL per docs ---
        # Example:
        # /api/ticks/?s=AAPL&from=1694455200&to=1694541600&limit=5&fmt=json
        url = (
            f"{EODHD_API_BASE}/ticks/"
            f"?s={ticker}"
            f"&from={f_ts}"
            f"&to={t_ts}"
            f"&limit={limit}"
            f"&fmt={fmt}"
        )
        if api_token:
            url += f"&api_token={api_token}"  # otherwise make_request appends env token

        # --- Request ---
        data = await make_request(url)

        # --- Normalize / return ---
        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        # For CSV, make_request may return text; wrap if needed. JSON is passed through.
        try:
            return json.dumps(data, indent=2)
        except Exception:
            if isinstance(data, str):
                return json.dumps({"csv": data}, indent=2)
            return _err("Unexpected response format from API.")
