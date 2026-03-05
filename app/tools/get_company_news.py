#get_company_news.py

import json
import re
from datetime import datetime
from typing import Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_FMT = {"json", "xml"}

def _valid_date(d: Optional[str]) -> bool:
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
    async def get_company_news(
        ticker: Optional[str] = None,        # maps to 's'
        tag: Optional[str] = None,           # maps to 't'
        start_date: Optional[str] = None,    # maps to 'from' (YYYY-MM-DD)
        end_date: Optional[str] = None,      # maps to 'to' (YYYY-MM-DD)
        limit: int = 50,                     # 1..1000 (API default 50)
        offset: int = 0,                     # default 0
        fmt: str = "json",                   # 'json' or 'xml' (API default json)
        api_token: Optional[str] = None,     # per-call override
    ) -> str:
        """
        Financial News API (spec-aligned).

        Args:
            ticker (str, optional): SYMBOL.EXCHANGE_ID (e.g., 'AAPL.US'). Mapped to 's'.
            tag (str, optional): Topic tag (e.g., 'technology'). Mapped to 't'.
            start_date (str, optional): YYYY-MM-DD. Mapped to 'from'.
            end_date (str, optional): YYYY-MM-DD. Mapped to 'to'.
            limit (int): 1..1000 (default 50).
            offset (int): >= 0 (default 0).
            fmt (str): 'json' or 'xml' (default 'json').
            api_token (str, optional): Per-call token override; env token used if omitted.

        Returns:
            str: JSON string of articles (or {"xml": "..."} if fmt='xml' and your client returns text).
        """
        # --- Validate required conditions ---
        if not ticker and not tag:
            raise ToolError("Provide at least one of 'ticker' (s) or 'tag' (t).")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        if not _valid_date(start_date):
            raise ToolError("'start_date' must be YYYY-MM-DD when provided.")
        if not _valid_date(end_date):
            raise ToolError("'end_date' must be YYYY-MM-DD when provided.")
        if start_date and end_date:
            if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
                raise ToolError("'start_date' cannot be after 'end_date'.")

        if not isinstance(limit, int) or not (1 <= limit <= 1000):
            raise ToolError("'limit' must be an integer between 1 and 1000.")
        if not isinstance(offset, int) or offset < 0:
            raise ToolError("'offset' must be a non-negative integer.")

        # --- Build URL per docs ---
        url = f"{EODHD_API_BASE}/news?fmt={fmt}&limit={limit}&offset={offset}"
        if ticker:
            url += f"&s={ticker}"
        if tag:
            url += f"&t={tag}"
        if start_date:
            url += f"&from={start_date}"
        if end_date:
            url += f"&to={end_date}"
        if api_token:
            url += f"&api_token={api_token}"  # otherwise make_request will append env token

        # --- Request ---
        data = await make_request(url)

        # --- Normalize / return ---
        if data is None:
            raise ToolError("No response from API.")

        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        # Typical 'json' path: API returns a list of articles (or an object).
        try:
            return json.dumps(data, indent=2)
        except Exception:
            # If you adapt make_request to return raw text for 'xml', we wrap it.
            if isinstance(data, str):
                return json.dumps({"xml": data}, indent=2)
            raise ToolError("Unexpected response format from API.")

