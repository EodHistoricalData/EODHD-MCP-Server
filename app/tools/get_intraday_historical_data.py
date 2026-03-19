# get_intraday_historical_data.py

from datetime import datetime, timezone

from app.api_client import make_request
from app.config import EODHD_API_BASE
from app.formatter import sanitize_ticker
from app.response import format_json_response
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

ALLOWED_INTERVALS = {"1m", "5m", "1h"}  # per docs
ALLOWED_FMT = {"json", "csv"}

# Max allowed “from->to” span per docs (in days)
MAX_RANGE_DAYS = {
    "1m": 120,
    "5m": 600,
    "1h": 7200,
}


def _to_unix_seconds(dt_obj: datetime) -> int:
    """Convert aware/naive datetime to Unix seconds (UTC)."""
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=timezone.utc)
    else:
        dt_obj = dt_obj.astimezone(timezone.utc)
    return int(dt_obj.timestamp())


def _parse_date_to_unix(value: int | float | str) -> int | None:
    """
    Best-effort parser:
      - If it's numeric: treat as seconds (10+ digits) or ms (13 digits) and coerce to seconds.
      - If it's a string date/datetime, try many common formats and ISO-8601 variants.
      - Returns None when it cannot be parsed.
    """
    # --- Numeric branch ---
    if isinstance(value, (int, float)):
        iv = int(value)
        # Heuristic: if it's very large (e.g., 13-digit), assume milliseconds
        if iv > 10_000_000_000:  # ~ year 2286; safe ms detector
            iv //= 1000
        return iv if iv > 0 else None

    if not isinstance(value, str):
        return None

    s = value.strip()
    if not s:
        return None

    # Digits-only strings: seconds or milliseconds
    if s.isdigit():
        iv = int(s)
        if iv > 10_000_000_000:
            iv //= 1000
        return iv if iv > 0 else None

    # Handle trailing 'Z' ISO-8601
    # e.g. 2024-06-30T15:00:00Z
    if s.endswith("Z"):
        try:
            dt_obj = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return _to_unix_seconds(dt_obj)
        except Exception:
            pass

    # Try vanilla ISO-8601 first (without 'Z')
    try:
        # fromisoformat covers many variants: YYYY-MM-DD, with time, with offset, etc.
        dt_obj = datetime.fromisoformat(s)
        return _to_unix_seconds(dt_obj)
    except Exception:
        pass

    # If string looks like just a calendar date without time, we’ll try many formats
    # and assume 00:00:00 UTC.
    date_formats = [
        # ISO date
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        # Day-first
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%d-%m-%y",
        "%d/%m/%y",
        "%d.%m.%y",
        # Month-first (US)
        "%m-%d-%Y",
        "%m/%d/%Y",
        "%m.%d.%Y",
        "%m-%d-%y",
        "%m/%d/%y",
        "%m.%d.%y",
        # With time (no timezone)
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        # Month names
        "%b %d, %Y",
        "%d %b %Y",
        "%B %d, %Y",
        "%d %B %Y",
        "%b %d, %y",
        "%d %b %y",
        "%B %d, %y",
        "%d %B %y",
        # T-separated without timezone
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
    ]

    for fmt in date_formats:
        try:
            dt_obj = datetime.strptime(s, fmt)
            # If parsed is a date-only pattern (most are), treat as midnight UTC
            return _to_unix_seconds(dt_obj)
        except Exception:
            continue

    # Could not parse
    return None


def _coerce_from_to(
    from_raw: int | str | None,
    to_raw: int | str | None,
) -> tuple[int | None, int | None, str | None]:
    """
    Convert 'from'/'to' inputs (which may be unix seconds or a date string) to (from_ts, to_ts).
    Returns (from_ts, to_ts, error_message).
    """
    from_ts = None
    to_ts = None

    if from_raw is not None:
        from_ts = _parse_date_to_unix(from_raw)
        if not from_ts:
            return None, None, "'from_timestamp' (or its string form) is not a valid date/time."

    if to_raw is not None:
        to_ts = _parse_date_to_unix(to_raw)
        if not to_ts:
            return None, None, "'to_timestamp' (or its string form) is not a valid date/time."

    if from_ts is not None and to_ts is not None and from_ts > to_ts:
        return None, None, "'from_timestamp' cannot be greater than 'to_timestamp'."

    return from_ts, to_ts, None


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_intraday_historical_data(
        ticker: str,
        interval: str = "5m",
        # Now accept unix seconds or date strings for both:
        from_timestamp: int | str | None = None,
        to_timestamp: int | str | None = None,
        fmt: str = "json",
        split_dt: bool | None = False,
        api_token: str | None = None,
    ) -> list:
        """

        Get historical intraday OHLCV candles at 1-minute, 5-minute, or 1-hour intervals.
        Use for intraday price analysis, short-term patterns, and high-resolution charting.
        Accepts date strings or Unix timestamps for the time range.
        Max range depends on interval: 1m=120 days, 5m=600 days, 1h=7200 days.
        For daily/weekly/monthly end-of-day bars, use get_historical_stock_prices instead.
        For current live price, use get_live_price_data instead.

        Args:
            ticker (str): SYMBOL.EXCHANGE_ID, e.g. 'AAPL.US'.
            interval (str): One of {'1m','5m','1h'}. Default '5m'.
            from_timestamp (int|str, optional): Start as Unix seconds OR a date string
                (auto-detected). Examples: 1704067200, '2024-01-01', '01-01-24', '01/01/2024',
                '2024-01-01T15:30:00Z', 'Jan 1, 2024'.
            to_timestamp (int|str, optional): End as Unix seconds OR a date string (auto-detected).
            fmt (str): 'json' or 'csv'. Default 'json'.
            split_dt (bool, optional): If True, adds 'split-dt=1' to split date/time fields.
            api_token (str, optional): Per-call token override; env token used if omitted.

        Notes:
            - If no 'from'/'to' provided, API returns last 120 days by default (per docs).
            - Max span depends on interval:
                1m -> 120 days, 5m -> 600 days, 1h -> 7200 days.

        Returns:
            Array of intraday bar records, each with:
            - timestamp (int): Unix epoch seconds
            - gmtoffset (int): GMT offset in seconds for the exchange
            - datetime (str): human-readable datetime (YYYY-MM-DD HH:MM:SS)
            - open, high, low, close (float): bar OHLC
            - volume (int): shares traded in this bar

        Notes:
            - If no 'from'/'to' provided, API returns last 120 days by default (per docs).
            - Max span depends on interval:
                1m -> 120 days, 5m -> 600 days, 1h -> 7200 days.

        """

        # --- Validate required/typed params ---
        ticker = sanitize_ticker(ticker)

        if interval not in ALLOWED_INTERVALS:
            raise ToolError(f"Invalid 'interval'. Allowed: {sorted(ALLOWED_INTERVALS)}")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        # --- Coerce 'from'/'to' into Unix seconds (auto-detect strings, ms, etc.) ---
        from_ts, to_ts, err = _coerce_from_to(from_timestamp, to_timestamp)
        if err:
            raise ToolError(err)

        # --- Enforce documented maximum range ---
        if from_ts is not None and to_ts is not None:
            span_seconds = to_ts - from_ts
            max_days = MAX_RANGE_DAYS[interval]
            if span_seconds > max_days * 86400:
                raise ToolError(f"Requested range exceeds maximum for interval '{interval}'. Max is {max_days} days.")

        # --- Build URL ---
        # Base: /api/intraday/{ticker}?fmt=...&interval=...&from=...&to=...&split-dt=1
        url = f"{EODHD_API_BASE}/intraday/{ticker}?fmt={fmt}&interval={interval}"

        if from_ts is not None:
            url += f"&from={from_ts}"
        if to_ts is not None:
            url += f"&to={to_ts}"
        if split_dt:
            url += "&split-dt=1"

        # Per-call token override; make_request() will append env token if none present.
        if api_token:
            url += f"&api_token={api_token}"

        # --- Request ---
        data = await make_request(url)

        # --- Normalize errors / outputs ---
        if data is None:
            raise ToolError("No response from API.")

        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        # For csv: if you later adapt make_request to return text for fmt='csv',
        # we wrap it as {"csv": "..."} so the MCP tool consistently returns a JSON string.
        try:
            return format_json_response(data)
        except Exception:
            if isinstance(data, str):
                return format_json_response({"csv": data})
            raise ToolError("Unexpected response format from API.")
