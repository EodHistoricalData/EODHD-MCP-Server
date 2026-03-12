"""Shared input formatting helpers for EODHD MCP tools.

Unlike strict validators, these helpers coerce flexible user input into
the specific format each tool/API endpoint expects.  The goal is to keep
tools working with the widest possible input from the agent — not to
reject requests when formats don't match exactly.
"""

import logging
import re
from datetime import datetime, timezone

from fastmcp.exceptions import ToolError

logger = logging.getLogger("eodhd-mcp.formatter")

# Characters that would break a URL path segment or query string.
_URL_UNSAFE_RE = re.compile(r"[?&#/\s]")

# Strict allowlist for values interpolated into prompt text.
# Only letters, digits, dots, hyphens, and underscores — max 20 chars.
_PROMPT_SAFE_RE = re.compile(r"^[A-Za-z0-9._-]{1,20}$")


# ── Ticker / exchange sanitisers ─────────────────────────────────────────


def sanitize_prompt_param(value: str, param_name: str = "parameter") -> str:
    """Validate and return a value safe for interpolation into prompt text.

    Only allows alphanumeric characters, dots, hyphens, and underscores
    (max 20 chars). Rejects anything that could be used for prompt injection.
    """
    if not value or not isinstance(value, str):
        raise ToolError(f"Parameter '{param_name}' is required and must be a non-empty string.")
    value = value.strip().upper()
    if not _PROMPT_SAFE_RE.match(value):
        raise ToolError(
            f"Parameter '{param_name}' must contain only letters, digits, dots, hyphens, "
            f"or underscores (max 20 chars). Got: {value!r}"
        )
    return value


def sanitize_ticker(ticker: str, param_name: str = "ticker") -> str:
    """Strip whitespace and reject only characters that break the URL."""
    if not ticker or not isinstance(ticker, str):
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
    if not code or not isinstance(code, str):
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
