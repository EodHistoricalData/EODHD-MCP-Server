# get_us_tick_data.py
import json

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

ALLOWED_FMT = {"json", "csv"}


def _to_int(name: str, v: int | str | None) -> int | None:
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
        ticker: str,  # maps to s=
        from_timestamp: int | str,  # UNIX seconds (UTC)
        to_timestamp: int | str,  # UNIX seconds (UTC)
        limit: int = 1000,  # max number of ticks returned
        fmt: str = "json",  # 'json' | 'csv'
        api_token: str | None = None,  # per-call override
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
            raise ToolError("Parameter 'ticker' is required (e.g., 'AAPL' or 'AAPL.US').")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        try:
            f_ts = _to_int("from_timestamp", from_timestamp)
            t_ts = _to_int("to_timestamp", to_timestamp)
        except ValueError as ve:
            raise ToolError(str(ve))

        if f_ts is None or t_ts is None:
            raise ToolError("'from_timestamp' and 'to_timestamp' are required (UNIX seconds).")
        if f_ts < 0 or t_ts < 0:
            raise ToolError("Timestamps must be non-negative UNIX seconds.")
        if f_ts > t_ts:
            raise ToolError("'from_timestamp' cannot be greater than 'to_timestamp'.")

        if not isinstance(limit, int) or limit <= 0:
            raise ToolError("'limit' must be a positive integer.")

        # --- Build URL per docs ---
        # Example:
        # /api/ticks/?s=AAPL&from=1694455200&to=1694541600&limit=5&fmt=json
        url = f"{EODHD_API_BASE}/ticks/?s={ticker}&from={f_ts}&to={t_ts}&limit={limit}&fmt={fmt}"
        if api_token:
            url += f"&api_token={api_token}"  # otherwise make_request appends env token

        # --- Request ---
        data = await make_request(url)

        # --- Normalize / return ---
        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        # For CSV, make_request may return text; wrap if needed. JSON is passed through.
        try:
            return json.dumps(data, indent=2)
        except Exception:
            if isinstance(data, str):
                return json.dumps({"csv": data}, indent=2)
            raise ToolError("Unexpected response format from API.")
