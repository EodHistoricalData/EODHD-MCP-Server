# app/input_formatter.py
"""Shared input formatting helpers for EODHD MCP tools.

Unlike strict validators, these helpers coerce flexible user input into
the specific format each tool/API endpoint expects.  The goal is to keep
tools working with the widest possible input from the agent — not to
reject requests when formats don't match exactly.
"""

import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus, urlencode

from fastmcp.exceptions import ToolError

logger = logging.getLogger("eodhd-mcp.formatter")

# Characters that would break a URL path segment or query string.
_URL_UNSAFE_RE = re.compile(r"[?&#/\s]")


# ── Query-string helpers ─────────────────────────────────────────────────


def build_url(path: str, params: dict[str, str | int | float | bool | None] | None = None) -> str:
    """Build a full EODHD API URL with properly encoded query string.
    *path* is relative to ``EODHD_API_BASE`` (leading ``/`` is stripped).
    *params* values that are ``None`` or ``""`` are silently dropped so callers
    can pass every optional parameter without ``if`` guards.
    """
    from app.config import EODHD_API_BASE  # late import avoids circular deps

    base = f"{EODHD_API_BASE}/{path.lstrip('/')}"
    if not params:
        return base
    clean: dict[str, str | int | float] = {}
    for k, v in params.items():
        if v is None or v == "":
            continue
        if isinstance(v, bool):
            clean[k] = 1 if v else 0
        else:
            clean[k] = v
    if not clean:
        return base
    return f"{base}?{urlencode(clean)}"


def build_query_param(key: str, val: str | int | float | None) -> str:
    """Return ``&key=value`` (URL-encoded) or ``""`` when *val* is ``None``/empty."""
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def build_query_bool(key: str, val: bool | None) -> str:
    """Return ``&key=1`` / ``&key=0`` or ``""`` when *val* is ``None``."""
    if val is None:
        return ""
    return f"&{key}={(1 if val else 0)}"


# ── Ticker / exchange sanitisers ─────────────────────────────────────────


def sanitize_ticker(ticker: str, param_name: str = "ticker") -> str:
    """Strip whitespace and reject only characters that break the URL."""
    if not isinstance(ticker, str) or not ticker.strip():
        raise ToolError(f"Parameter '{param_name}' is required and must be a non-empty string.")
    ticker = ticker.strip()
    if _URL_UNSAFE_RE.search(ticker):
        raise ToolError(
            f"Parameter '{param_name}' contains characters that would break the request URL "
            f"(spaces, ?, &, #, /). Got: {ticker!r}"
        )
    return ticker


def sanitize_exchange(code: str, param_name: str = "exchange_code") -> str:
    """Strip whitespace and reject only characters that break the URL."""
    if not isinstance(code, str) or not code.strip():
        raise ToolError(f"Parameter '{param_name}' is required and must be a non-empty string.")
    code = code.strip()
    if _URL_UNSAFE_RE.search(code):
        raise ToolError(
            f"Parameter '{param_name}' contains characters that would break the request URL "
            f"(spaces, ?, &, #, /). Got: {code!r}"
        )
    return code


# ── Date / time formats tried during parsing ─────────────────────────────

_DATE_FORMATS = [
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


# ── Internal helpers ──────────────────────────────────────────────────────


def _to_unix_seconds(dt_obj: datetime) -> int:
    """Convert aware/naive datetime to Unix seconds (UTC)."""
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=timezone.utc)
    else:
        dt_obj = dt_obj.astimezone(timezone.utc)
    return int(dt_obj.timestamp())


def _parse_to_datetime(value: int | float | str) -> datetime | None:
    """Best-effort parser: numeric (unix seconds/ms), ISO-8601, or common
    date strings.  Returns a *datetime* object, or ``None`` if unparseable.
    """
    # ── Numeric branch ────────────────────────────────────────────────
    if isinstance(value, (int, float)):
        iv = int(value)
        if iv > 10_000_000_000:  # likely milliseconds
            iv //= 1000
        if iv <= 0:
            return None
        try:
            return datetime.fromtimestamp(iv, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None

    if not isinstance(value, str):
        return None

    s = value.strip()
    if not s:
        return None

    # Digits-only → unix seconds or milliseconds
    if s.isdigit():
        iv = int(s)
        if iv > 10_000_000_000:
            iv //= 1000
        if iv <= 0:
            return None
        try:
            return datetime.fromtimestamp(iv, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None

    # Trailing 'Z' ISO-8601
    if s.endswith("Z"):
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            pass

    # Vanilla ISO-8601
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass

    # Common date/datetime patterns
    for fmt in _DATE_FORMATS:
        try:
            dt_obj = datetime.strptime(s, fmt)
            return dt_obj.replace(tzinfo=timezone.utc)
        except Exception:
            continue

    return None


# ── Public API ────────────────────────────────────────────────────────────


def format_date(
    value: int | float | str | None,
    output_format: str = "%Y-%m-%d",
) -> str | None:
    """Coerce *any* recognisable date/time input into a specific string format.

    Parameters
    ----------
    value:
        The raw input — may be a unix timestamp (int/float), a date string
        in virtually any common format, or ``None``.
    output_format:
        A :func:`datetime.strftime` format string.  Defaults to
        ``"%Y-%m-%d"`` (the format used by most EODHD endpoints).

    Returns
    -------
    str | None
        The formatted date string, or ``None`` if *value* is ``None`` or
        could not be parsed.  **Never raises** — unparseable values are
        silently returned as ``None`` so the caller can decide how to
        handle them.
    """
    if value is None:
        return None

    dt = _parse_to_datetime(value)
    if dt is None:
        logger.debug("Could not parse date value: %r", value)
        return None

    return dt.strftime(output_format)


def format_date_ymd(value: int | float | str | None) -> str | None:
    """Shorthand: format to ``YYYY-MM-DD`` (used by EOD, technical, etc.)."""
    return format_date(value, "%Y-%m-%d")


def coerce_date_param(
    value: int | float | str | None,
    param_name: str = "date",
) -> str | None:
    """Coerce a flexible date input to ``YYYY-MM-DD`` or raise :class:`ToolError`.

    Returns ``None`` when *value* is ``None`` (i.e. the parameter was omitted).
    Raises ``ToolError`` when *value* is non-empty but unparseable.
    """
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None

    from fastmcp.exceptions import ToolError  # late import avoids circular deps

    result = format_date_ymd(value)
    if result is None:
        raise ToolError(f"'{param_name}' could not be parsed as a date. Got: {value!r}")
    return result


def validate_date_range(
    start: str | None,
    end: str | None,
    start_name: str = "start_date",
    end_name: str = "end_date",
) -> None:
    """Raise :class:`ToolError` if *start* is after *end*.

    Both values must already be ``YYYY-MM-DD`` strings (as returned by
    :func:`coerce_date_param`).  ``None`` on either side is treated as
    unbounded.
    """
    if start and end and start > end:
        from fastmcp.exceptions import ToolError

        raise ToolError(f"'{start_name}' cannot be after '{end_name}'.")


def format_date_unix(value: int | float | str | None) -> int | None:
    """Coerce any date input to Unix seconds (UTC).

    Used by intraday and tick-data tools that expect integer timestamps.
    Returns ``None`` if *value* is ``None`` or unparseable.
    """
    if value is None:
        return None

    dt = _parse_to_datetime(value)
    if dt is None:
        logger.debug("Could not parse date value to unix: %r", value)
        return None

    return _to_unix_seconds(dt)


def coerce_timestamp_param(
    value: int | float | str | None,
    param_name: str = "timestamp",
) -> int | None:
    """Coerce a flexible date/time input to Unix seconds (UTC) or raise :class:`ToolError`.

    Accepts Unix timestamps (seconds or milliseconds), ISO-8601 strings,
    and common date/datetime formats.  Returns ``None`` when *value* is
    ``None`` (i.e. the parameter was omitted).
    Raises ``ToolError`` when *value* is non-empty but unparseable.
    """
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None

    from fastmcp.exceptions import ToolError  # late import avoids circular deps

    result = format_date_unix(value)
    if result is None:
        raise ToolError(f"'{param_name}' could not be parsed as a date/time. Got: {value!r}")
    return result


def validate_timestamp_range(
    start: int | None,
    end: int | None,
    start_name: str = "from_timestamp",
    end_name: str = "to_timestamp",
) -> None:
    """Raise :class:`ToolError` if *start* is after *end*.

    Both values must already be Unix seconds (as returned by
    :func:`coerce_timestamp_param`).  ``None`` on either side is treated as
    unbounded.
    """
    if start is not None and end is not None and start > end:
        from fastmcp.exceptions import ToolError

        raise ToolError(f"'{start_name}' cannot be after '{end_name}'.")
