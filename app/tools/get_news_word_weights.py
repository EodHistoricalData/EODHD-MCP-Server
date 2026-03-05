#get_news_word_weights.py

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
    async def get_news_word_weights(
        ticker: str,                      # maps to 's'
        start_date: Optional[str] = None, # maps to filter[date_from]
        end_date: Optional[str] = None,   # maps to filter[date_to]
        limit: Optional[int] = None,      # maps to page[limit]
        fmt: str = "json",
        api_token: Optional[str] = None,
    ) -> str:
        """
        News Word Weights API (GET /api/news-word-weights)

        Args:
            ticker (str): Symbol to analyze (e.g., 'AAPL.US'); mapped to 's'.
            start_date (str, optional): YYYY-MM-DD; mapped to filter[date_from].
            end_date (str, optional): YYYY-MM-DD; mapped to filter[date_to].
            limit (int, optional): Number of top words; mapped to page[limit].
            fmt (str): 'json' (default). (CSV/XML not documented for this endpoint.)
            api_token (str, optional): Per-call token override.

        Returns:
            str: JSON like {"data": {...}, "meta": {...}, "links": {...}} or {"error": "..."}.

        Examples:
            "Top news keywords for Apple last month" → ticker="AAPL.US", start_date="2026-02-01", end_date="2026-02-28"
            "Nvidia word weights, top 20" → ticker="NVDA.US", limit=20
            "Amazon news themes in Q1 2026" → ticker="AMZN.US", start_date="2026-01-01", end_date="2026-03-06"
        """
        if not ticker or not isinstance(ticker, str):
            raise ToolError("Parameter 'ticker' is required (e.g., 'AAPL.US').")

        if fmt != "json":
            raise ToolError("Only 'json' is supported for this endpoint.")

        if not _valid_date(start_date):
            raise ToolError("'start_date' must be YYYY-MM-DD when provided.")
        if not _valid_date(end_date):
            raise ToolError("'end_date' must be YYYY-MM-DD when provided.")
        if start_date and end_date:
            if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
                raise ToolError("'start_date' cannot be after 'end_date'.")

        if limit is not None:
            if not isinstance(limit, int) or limit <= 0:
                raise ToolError("'limit' must be a positive integer when provided.")

        # Build URL with nested filter/page params
        # Example:
        # /api/news-word-weights?s=AAPL.US&filter[date_from]=2025-04-08&filter[date_to]=2025-04-16&page[limit]=10&fmt=json
        url = f"{EODHD_API_BASE}/news-word-weights?s={ticker}&fmt={fmt}"
        if start_date:
            url += f"&filter[date_from]={start_date}"
        if end_date:
            url += f"&filter[date_to]={end_date}"
        if limit is not None:
            url += f"&page[limit]={limit}"
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
