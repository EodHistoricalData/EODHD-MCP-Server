# get_support_resistance_levels.py

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

ALLOWED_METHODS = {"classic", "fibonacci", "woodie", "camarilla", "demark"}


def _valid_date(s: str) -> bool:
    if not isinstance(s, str) or not DATE_RE.match(s):
        return False
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _calc_classic(high: float, low: float, close: float) -> dict:
    """Classic (Floor) Pivot Points."""
    pp = (high + low + close) / 3
    return {
        "method": "classic",
        "pivot_point": round(pp, 4),
        "resistance_1": round((2 * pp) - low, 4),
        "resistance_2": round(pp + (high - low), 4),
        "resistance_3": round(high + 2 * (pp - low), 4),
        "support_1": round((2 * pp) - high, 4),
        "support_2": round(pp - (high - low), 4),
        "support_3": round(low - 2 * (high - pp), 4),
    }


def _calc_fibonacci(high: float, low: float, close: float) -> dict:
    """Fibonacci Pivot Points."""
    pp = (high + low + close) / 3
    r = high - low
    return {
        "method": "fibonacci",
        "pivot_point": round(pp, 4),
        "resistance_1": round(pp + 0.382 * r, 4),
        "resistance_2": round(pp + 0.618 * r, 4),
        "resistance_3": round(pp + 1.000 * r, 4),
        "support_1": round(pp - 0.382 * r, 4),
        "support_2": round(pp - 0.618 * r, 4),
        "support_3": round(pp - 1.000 * r, 4),
    }


def _calc_woodie(high: float, low: float, close: float) -> dict:
    """Woodie Pivot Points (extra weight on close)."""
    pp = (high + low + 2 * close) / 4
    return {
        "method": "woodie",
        "pivot_point": round(pp, 4),
        "resistance_1": round((2 * pp) - low, 4),
        "resistance_2": round(pp + (high - low), 4),
        "support_1": round((2 * pp) - high, 4),
        "support_2": round(pp - (high - low), 4),
    }


def _calc_camarilla(high: float, low: float, close: float) -> dict:
    """Camarilla Pivot Points."""
    r = high - low
    return {
        "method": "camarilla",
        "pivot_point": round((high + low + close) / 3, 4),
        "resistance_1": round(close + r * 1.1 / 12, 4),
        "resistance_2": round(close + r * 1.1 / 6, 4),
        "resistance_3": round(close + r * 1.1 / 4, 4),
        "resistance_4": round(close + r * 1.1 / 2, 4),
        "support_1": round(close - r * 1.1 / 12, 4),
        "support_2": round(close - r * 1.1 / 6, 4),
        "support_3": round(close - r * 1.1 / 4, 4),
        "support_4": round(close - r * 1.1 / 2, 4),
    }


def _calc_demark(high: float, low: float, close: float, open_: float) -> dict:
    """DeMark Pivot Points."""
    if close < open_:
        x = high + 2 * low + close
    elif close > open_:
        x = 2 * high + low + close
    else:
        x = high + low + 2 * close
    pp = x / 4
    return {
        "method": "demark",
        "pivot_point": round(pp, 4),
        "resistance_1": round(x / 2 - low, 4),
        "support_1": round(x / 2 - high, 4),
    }


CALC_MAP = {
    "classic": _calc_classic,
    "fibonacci": _calc_fibonacci,
    "woodie": _calc_woodie,
    "camarilla": _calc_camarilla,
    "demark": _calc_demark,
}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_support_resistance_levels(
        ticker: str,
        method: str = "classic",
        period: str = "d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        api_token: Optional[str] = None,
    ) -> str:
        """
        Calculate pivot-point-based support and resistance levels for any stock, ETF, index, or crypto.

        Fetches historical OHLCV data and computes support/resistance levels using one of five
        standard pivot point methods: Classic (Floor), Fibonacci, Woodie, Camarilla, or DeMark.
        Each record in the result corresponds to one bar from the price history, with the calculated
        levels that traders use to identify potential reversal zones, entry/exit points, and stop-loss placement.

        Formulas:
            Classic:    PP = (H + L + C) / 3;  R1 = 2·PP − L;  S1 = 2·PP − H;  R2 = PP + (H − L);  S2 = PP − (H − L)
            Fibonacci:  PP = (H + L + C) / 3;  R1 = PP + 0.382·(H − L);  S1 = PP − 0.382·(H − L)
            Woodie:     PP = (H + L + 2·C) / 4  (extra weight on close)
            Camarilla:  Uses close ± range × multipliers (1.1/12, 1.1/6, 1.1/4, 1.1/2)
            DeMark:     X depends on open vs close relationship; PP = X/4

        Args:
            ticker: Symbol in SYMBOL.EXCHANGE format (e.g. 'AAPL.US').
                    If you only have a company name or ISIN, call resolve_ticker first.
            method: Pivot point method — 'classic', 'fibonacci', 'woodie', 'camarilla', or 'demark'. Default 'classic'.
            period: Price bar period — 'd' (daily), 'w' (weekly), 'm' (monthly). Default 'd'.
            start_date: Start date in YYYY-MM-DD format (optional).
            end_date: End date in YYYY-MM-DD format (optional).
            api_token: Override API token for this call (optional).

        Returns:
            Array of objects, each with:
            - date (str): YYYY-MM-DD
            - open, high, low, close (float): OHLC prices for the bar
            - method (str): calculation method used
            - pivot_point (float): the central pivot level
            - resistance_1, resistance_2, resistance_3 (float): resistance levels (count varies by method)
            - support_1, support_2, support_3 (float): support levels (count varies by method)

        Examples:
            "Classic pivot points for Apple last month" → ticker="AAPL.US", method="classic", start_date="2026-02-01"
            "Fibonacci support/resistance for Bitcoin weekly" → ticker="BTC-USD.CC", method="fibonacci", period="w"
            "Camarilla levels for Tesla in 2025" → ticker="TSLA.US", method="camarilla", start_date="2025-01-01", end_date="2025-12-31"

        """
        # --- Validation ---
        if not ticker or not isinstance(ticker, str):
            raise ToolError("Parameter 'ticker' is required and must be a string (e.g., 'AAPL.US').")

        method = method.strip().lower() if isinstance(method, str) else "classic"
        if method not in ALLOWED_METHODS:
            raise ToolError(
                f"Invalid 'method'. Allowed: {', '.join(sorted(ALLOWED_METHODS))}"
            )

        allowed_periods = {"d", "w", "m"}
        if period not in allowed_periods:
            raise ToolError(f"Invalid 'period'. Allowed: {sorted(allowed_periods)}")

        if start_date is not None and not _valid_date(start_date):
            raise ToolError("Parameter 'start_date' must be YYYY-MM-DD when provided.")
        if end_date is not None and not _valid_date(end_date):
            raise ToolError("Parameter 'end_date' must be YYYY-MM-DD when provided.")
        if start_date and end_date:
            if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
                raise ToolError("'start_date' cannot be after 'end_date'.")

        # --- Fetch OHLCV data ---
        url = f"{EODHD_API_BASE}/eod/{ticker}?period={period}&order=a&fmt=json"
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
        if not isinstance(data, list) or len(data) == 0:
            raise ToolError("No price data available for the given ticker and date range.")

        # --- Calculate support/resistance for each bar ---
        calc_fn = CALC_MAP[method]
        results = []
        for bar in data:
            h = bar.get("high")
            l = bar.get("low")
            c = bar.get("close")
            o = bar.get("open")
            if h is None or l is None or c is None:
                continue

            if method == "demark":
                if o is None:
                    continue
                levels = calc_fn(h, l, c, o)
            else:
                levels = calc_fn(h, l, c)

            results.append({
                "date": bar.get("date"),
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                **levels,
            })

        if not results:
            raise ToolError("Could not compute levels — no valid OHLC bars found.")

        return json.dumps(results, indent=2)
