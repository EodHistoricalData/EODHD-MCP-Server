# get_exchange_details.py

import json
import re
from datetime import datetime

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _valid_date(d: str | None) -> bool:
    if d is None:
        return True
    if not DATE_RE.match(d):
        return False
    try:
        datetime.strptime(d, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_exchange_details(
        exchange_code: str,  # e.g., "US", "LSE", "XETRA"
        start_date: str | None = None,  # maps to 'from' (YYYY-MM-DD)
        end_date: str | None = None,  # maps to 'to'   (YYYY-MM-DD)
        fmt: str = "json",  # API supports json (we gate to json here)
        api_token: str | None = None,  # per-call token override
    ) -> str:
        """
        Get Exchange Details & Trading Hours (GET /api/exchange-details/{EXCHANGE_CODE})

        Returns metadata for the exchange, including:
          - Timezone
          - isOpen (boolean)
          - TradingHours (open/close, UTC equivalents, working days, lunch hours if present)
          - ExchangeHolidays (bank/official; ~6 months back & forward; supports 'from'/'to')
          - ActiveTickers (last 2 months), UpdatedTickers (today), PreviousDayUpdatedTickers

        Args:
            exchange_code (str): Exchange code (e.g., 'US', 'LSE', 'XETRA').
            start_date (str, optional): YYYY-MM-DD; mapped to 'from' for holidays filter.
            end_date (str, optional):   YYYY-MM-DD; mapped to 'to'   for holidays filter.
            fmt (str): 'json' only (default).
            api_token (str, optional): Per-call token override (env token otherwise).

        Returns:
            str: JSON string with exchange details or {"error": "..."} on failure.
        """
        # --- Validate inputs ---
        if not exchange_code or not isinstance(exchange_code, str):
            raise ToolError("Parameter 'exchange_code' is required (e.g., 'US', 'LSE').")

        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        if not _valid_date(start_date):
            raise ToolError("'start_date' must be YYYY-MM-DD when provided.")
        if not _valid_date(end_date):
            raise ToolError("'end_date' must be YYYY-MM-DD when provided.")
        if start_date and end_date:
            if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
                raise ToolError("'start_date' cannot be after 'end_date'.")

        # --- Build URL per docs ---
        url = f"{EODHD_API_BASE}/exchange-details/{exchange_code}?fmt={fmt}"
        if start_date:
            url += f"&from={start_date}"
        if end_date:
            url += f"&to={end_date}"
        if api_token:
            url += f"&api_token={api_token}"  # otherwise make_request adds env token

        # --- Request ---
        data = await make_request(url)

        # --- Normalize response ---
        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
