# get_insider_transactions.py

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
    async def get_insider_transactions(
        start_date: str | None = None,  # maps to 'from' (YYYY-MM-DD)
        end_date: str | None = None,  # maps to 'to'   (YYYY-MM-DD)
        limit: int = 100,  # 1..1000, default 100
        symbol: str | None = None,  # maps to 'code' (e.g., 'AAPL' or 'AAPL.US')
        fmt: str = "json",  # API returns json; we gate to json
        api_token: str | None = None,  # per-call token override
    ) -> str:
        """
        Insider Transactions API (SEC Form 4)
        GET /api/insider-transactions

        Args:
            start_date (str, optional): 'from' in YYYY-MM-DD. Defaults to ~1 year ago by API if omitted.
            end_date (str, optional):   'to'   in YYYY-MM-DD. Defaults to today by API if omitted.
            limit (int): Number of entries to return, 1..1000. Default 100.
            symbol (str, optional): Filter by ticker (API param 'code'), e.g. 'AAPL' or 'AAPL.US'.
            fmt (str): Only 'json' is supported by this tool.
            api_token (str, optional): Per-call token; env token used if omitted.

        Returns:
            str: JSON array of insider transactions or {"error": "..."} on failure.

        Notes:
            • Each request consumes 10 API calls (per docs).
            • Transaction codes in results include 'P' (Purchase) and 'S' (Sale).
        """
        # --- Validate inputs ---
        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        if not isinstance(limit, int) or not (1 <= limit <= 1000):
            raise ToolError("'limit' must be an integer between 1 and 1000.")

        if not _valid_date(start_date):
            raise ToolError("'start_date' must be YYYY-MM-DD when provided.")
        if not _valid_date(end_date):
            raise ToolError("'end_date' must be YYYY-MM-DD when provided.")
        if start_date and end_date:
            if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
                raise ToolError("'start_date' cannot be after 'end_date'.")

        # --- Build URL per docs ---
        # Example:
        # /api/insider-transactions?fmt=json&limit=100&from=2024-03-01&to=2024-03-02&code=AAPL.US
        url = f"{EODHD_API_BASE}/insider-transactions?fmt={fmt}&limit={limit}"
        if start_date:
            url += f"&from={start_date}"
        if end_date:
            url += f"&to={end_date}"
        if symbol:
            url += f"&code={symbol}"
        if api_token:
            url += f"&api_token={api_token}"  # otherwise make_request appends env token

        # --- Request ---
        data = await make_request(url)

        # --- Normalize / return ---
        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
