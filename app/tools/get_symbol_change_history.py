#get_symbol_change_history.py

import json
import re
from datetime import datetime
from typing import Optional

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)

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
    async def get_symbol_change_history(
        start_date: Optional[str] = None,  # maps to 'from' (YYYY-MM-DD)
        end_date: Optional[str] = None,    # maps to 'to'   (YYYY-MM-DD)
        fmt: str = "json",                 # API returns json here; we gate to json
        api_token: Optional[str] = None,   # per-call token override
    ) -> str:
        """
        Symbol Change History (US-only for now)
        GET /api/symbol-change-history

        Args:
            start_date (str, optional): 'from' in YYYY-MM-DD (e.g., '2022-10-01').
            end_date (str, optional):   'to' in YYYY-MM-DD   (e.g., '2022-11-01').
            fmt (str): 'json' (default).
            api_token (str, optional): Per-call token override; env token used if omitted.

        Notes:
            - History starts from 2022-07-22; endpoint updated daily.
            - Only **US** exchanges are supported currently.
        Returns:
            str: JSON array of changes with fields:
                 exchange, old_symbol, new_symbol, company_name, effective
        """
        # Validate inputs
        if fmt != "json":
            return _err("Only 'json' is supported by this tool.")

        if not _valid_date(start_date):
            return _err("'start_date' must be YYYY-MM-DD when provided.")
        if not _valid_date(end_date):
            return _err("'end_date' must be YYYY-MM-DD when provided.")
        if start_date and end_date:
            if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
                return _err("'start_date' cannot be after 'end_date'.")

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
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected response format from API.")
