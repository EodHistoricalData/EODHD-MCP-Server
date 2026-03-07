# get_sentiment_data.py

import json
import re
from collections.abc import Iterable
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


def _normalize_symbols(symbols: Iterable[str]) -> str:
    # Turn a sequence like ["AAPL.US","BTC-USD.CC"] into "AAPL.US,BTC-USD.CC"
    return ",".join(s.strip() for s in symbols if s and str(s).strip())


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_sentiment_data(
        symbols: str,
        start_date: str | None = None,  # maps to 'from' (YYYY-MM-DD)
        end_date: str | None = None,  # maps to 'to'   (YYYY-MM-DD)
        fmt: str = "json",
        api_token: str | None = None,
    ) -> str:
        """
        Sentiment Data API (GET /api/sentiments)

        Args:
            symbols (str): One or more comma-separated tickers (e.g., 'AAPL.US,BTC-USD.CC').
            start_date (str, optional): YYYY-MM-DD, maps to 'from'.
            end_date (str, optional): YYYY-MM-DD, maps to 'to'.
            fmt (str): 'json' (default). (XML not documented for this endpoint.)
            api_token (str, optional): Per-call override; env token used if omitted.

        Returns:
            str: JSON with sentiment grouped by ticker or {"error": "..."}.
        """
        # Validate required
        if not symbols or not isinstance(symbols, str):
            raise ToolError("Parameter 'symbols' is required (comma-separated string).")

        if fmt != "json":
            raise ToolError("Only 'json' is supported for this endpoint.")

        if not _valid_date(start_date):
            raise ToolError("'start_date' must be YYYY-MM-DD when provided.")
        if not _valid_date(end_date):
            raise ToolError("'end_date' must be YYYY-MM-DD when provided.")
        if start_date and end_date:
            if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
                raise ToolError("'start_date' cannot be after 'end_date'.")

        # Build URL
        url = f"{EODHD_API_BASE}/sentiments?fmt={fmt}&s={symbols}"
        if start_date:
            url += f"&from={start_date}"
        if end_date:
            url += f"&to={end_date}"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
