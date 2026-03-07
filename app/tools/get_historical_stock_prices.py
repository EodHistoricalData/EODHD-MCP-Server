# get_historical_stock_prices.py

import json
from datetime import datetime

from app.api_client import make_request
from app.config import EODHD_API_BASE
from app.validators import validate_date, validate_ticker
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

ALLOWED_PERIODS = {"d", "w", "m"}  # daily, weekly, monthly (per docs)
ALLOWED_ORDER = {"a", "d"}  # ascending, descending (per docs)
ALLOWED_FMT = {"json", "csv"}  # default is csv in API, but we default to json here


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_historical_stock_prices(
        ticker: str,
        start_date: str | None = None,
        end_date: str | None = None,
        period: str = "d",
        order: str = "a",
        fmt: str = "json",
        filter: str | None = None,  # e.g., "last_close", "last_volume"
        api_token: str | None = None,  # per-call override
    ) -> str:
        """
        End-Of-Day Historical Stock Market Data (EOD) — spec-aligned.

        Args:
            ticker (str): Symbol in SYMBOL.EXCHANGE format, e.g. 'AAPL.US'.
            start_date (str, optional): 'from' date in YYYY-MM-DD. If omitted, API returns full history (plan limits apply).
            end_date (str, optional): 'to' date in YYYY-MM-DD. If omitted, API returns up to most recent.
            period (str): 'd' (daily), 'w' (weekly), 'm' (monthly). Default 'd'.
            order (str): 'a' (ascending) or 'd' (descending). Default 'a'.
            fmt (str): 'json' or 'csv'. Default 'json'. (API default is csv.)
            filter (str, optional): e.g., 'last_close', 'last_volume' (works with fmt=json; returns a single value).
            api_token (str, optional): Override API token for this call. If not provided, env token is used.

        Returns:
            str: JSON string with data or {"error": "..."}.
                 If fmt='csv', returns CSV text embedded as a JSON string for consistency.
        """
        # --- Validate required/typed params ---
        ticker = validate_ticker(ticker)

        if period not in ALLOWED_PERIODS:
            raise ToolError(f"Invalid 'period'. Allowed values: {sorted(ALLOWED_PERIODS)}")

        if order not in ALLOWED_ORDER:
            raise ToolError(f"Invalid 'order'. Allowed values: {sorted(ALLOWED_ORDER)}")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed values: {sorted(ALLOWED_FMT)}")

        validate_date(start_date, "start_date")
        validate_date(end_date, "end_date")

        if start_date and end_date:
            if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
                raise ToolError("'start_date' cannot be after 'end_date'.")

        # --- Build URL per docs ---
        # Base: /api/eod/{ticker}
        # Params: period, order, from, to, fmt, (optional) filter, api_token
        url = f"{EODHD_API_BASE}/eod/{ticker}?period={period}&order={order}&fmt={fmt}"

        if start_date:
            url += f"&from={start_date}"
        if end_date:
            url += f"&to={end_date}"
        if filter:
            url += f"&filter={filter}"

        # Per-call token override; make_request() appends env token if none present.
        if api_token:
            url += f"&api_token={api_token}"

        # --- Execute request ---
        data = await make_request(url)

        # --- Transport/API errors ---
        if data is None:
            raise ToolError("No response from API.")

        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        # For CSV, make_request() will attempt .json() and fail; but our make_request currently returns response.json().
        # If you need raw CSV support, consider updating make_request to return text for fmt=csv.
        # Until then, we keep fmt=json by default. However, if the API returned a list (json), just dump it.
        try:
            return json.dumps(data, indent=2)
        except Exception:
            # If fmt=csv and make_request was adapted to return text, 'data' may already be a str.
            if isinstance(data, str):
                # Wrap CSV text into a JSON string for consistent MCP return type (string)
                return json.dumps({"csv": data}, indent=2)
            raise ToolError("Unexpected response format from API.")
