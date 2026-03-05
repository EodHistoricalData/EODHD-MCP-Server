#get_upcoming_splits.py

import json
from typing import Optional
from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def _q(key: str, val: Optional[str]) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_upcoming_splits(
        from_date: Optional[str] = None,  # YYYY-MM-DD → maps to 'from'
        to_date: Optional[str] = None,    # YYYY-MM-DD → maps to 'to'
        fmt: str = "json",                # 'json' or 'csv' (API default is csv)
        api_token: Optional[str] = None,  # per-call override; else env EODHD_API_KEY
    ) -> str:
        """
        Upcoming Splits API (/calendar/splits)

        Parameters:
          - from_date (YYYY-MM-DD): start date (maps to 'from'); server default = today
          - to_date   (YYYY-MM-DD): end date   (maps to 'to');   server default = today+7d
          - fmt: 'json' or 'csv'. API default is 'csv'; we default to 'json' for developer ergonomics.
          - api_token: optional override for per-call token

        Returns:
            Array of split records, each with:
            - code (str): ticker symbol
            - exchange (str): exchange code
            - optionable (str): whether options exist ('0' or '1')
            - date (str): split effective date
            - split (str): split ratio (e.g. '4/1')
            - oldShares (int): pre-split share count
            - newShares (int): post-split share count
        """
        fmt = (fmt or "json").lower()
        if fmt not in ("json", "csv"):
            raise ToolError("Invalid 'fmt'. Allowed values: 'json', 'csv'.")

        # Build URL
        url = f"{EODHD_API_BASE}/calendar/splits?1=1"
        if from_date:
            url += _q("from", from_date)
        if to_date:
            url += _q("to", to_date)
        url += _q("fmt", fmt)

        if api_token:
            url += _q("api_token", api_token)  # otherwise appended by make_request via env

        # Call upstream
        data = await make_request(url)
        if data is None:
            raise ToolError("No response from API.")


        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))
        # Format handling
        if fmt == "csv":
            if isinstance(data, str):
                return json.dumps({"fmt": "csv", "data": data}, indent=2)
            raise ToolError("Unexpected CSV response format from API.")

        # fmt == json
        try:
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected JSON response format from API.")
