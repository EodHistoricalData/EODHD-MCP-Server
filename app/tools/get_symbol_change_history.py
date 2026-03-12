# get_symbol_change_history.py

import re
from datetime import datetime

from app.api_client import make_request
from app.config import EODHD_API_BASE
from app.response import format_json_response
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
    async def get_symbol_change_history(
        start_date: str | None = None,  # maps to 'from' (YYYY-MM-DD)
        end_date: str | None = None,  # maps to 'to'   (YYYY-MM-DD)
        fmt: str = "json",  # API returns json here; we gate to json
        api_token: str | None = None,  # per-call token override
    ) -> list:
        """

        Get ticker symbol change history -- tracks when US stocks changed their ticker symbol or company name.
        Returns old symbol, new symbol, company name, exchange, and effective date. Data available from 2022-07-22, US exchanges only.
        Use when the user asks about ticker renames, symbol changes, rebranding events, or needs to map old tickers to new ones.
        This is the only tool for symbol/ticker change tracking.

        Args:
            start_date (str, optional): 'from' in YYYY-MM-DD (e.g., '2022-10-01').
            end_date (str, optional):   'to' in YYYY-MM-DD   (e.g., '2022-11-01').
            fmt (str): 'json' (default).
            api_token (str, optional): Per-call token override; env token used if omitted.


        Returns:
            Array of symbol change records, each with:
            - old_code (str): previous ticker symbol
            - old_exchange (str): previous exchange code
            - old_country (str): previous country code
            - new_code (str): new ticker symbol
            - new_exchange (str): new exchange code
            - new_country (str): new country code
            - date (str): effective date of change

        Examples:
            "Symbol changes this month" → start_date="2026-03-01", end_date="2026-03-06"
            "Ticker renames in 2025" → start_date="2025-01-01", end_date="2025-12-31"
            "Recent symbol changes last 90 days" → start_date="2025-12-06", end_date="2026-03-06"


        """
        # Validate inputs
        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        if not _valid_date(start_date):
            raise ToolError("'start_date' must be YYYY-MM-DD when provided.")
        if not _valid_date(end_date):
            raise ToolError("'end_date' must be YYYY-MM-DD when provided.")
        if start_date and end_date:
            if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
                raise ToolError("'start_date' cannot be after 'end_date'.")

        # Build URL
        # Example:
        # /api/symbol-change-history?from=2022-10-01&to=2022-11-01&fmt=json
        url = f"{EODHD_API_BASE}/symbol-change-history?fmt={fmt}"
        if start_date:
            url += f"&from={start_date}"
        if end_date:
            url += f"&to={end_date}"
        if api_token:
            url += f"&api_token={api_token}"  # otherwise make_request appends env token

        # Request
        data = await make_request(url)

        # Normalize / return
        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return format_json_response(data)
        except Exception:
            raise ToolError("Unexpected response format from API.")
