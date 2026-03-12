"""Tests for app.formatter — sanitize_ticker, sanitize_exchange, date functions.

Covers:
  - Security: injection, path traversal, whitespace bypass (BUG-1)
  - Date parsing: ISO, unix, common formats, ambiguity (BUG-2)
  - Edge cases: None, empty, non-string types
"""

import pytest
from app.formatter import (
    _parse_to_datetime,
    _to_unix_seconds,
    format_date,
    format_date_unix,
    format_date_ymd,
    sanitize_exchange,
    sanitize_ticker,
)
from fastmcp.exceptions import ToolError

# ---------------------------------------------------------------------------
# sanitize_ticker — valid inputs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("AAPL", "AAPL"),
        ("  AAPL  ", "AAPL"),
        ("BRK.B", "BRK.B"),
        ("AAPL.US", "AAPL.US"),
        ("BTC-USD", "BTC-USD"),
        ("A", "A"),
        ("GSPC.INDX", "GSPC.INDX"),
    ],
    ids=["plain", "whitespace-padded", "dot-class", "dot-exchange", "dash", "single-char", "index"],
)
def test_sanitize_ticker_valid(value, expected):
    assert sanitize_ticker(value) == expected


# ---------------------------------------------------------------------------
# sanitize_ticker — invalid inputs must raise ToolError
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "",
        None,
        123,
        "AAPL/US",
        "AAPL?token=x",
        "AAPL&x=1",
        "AAPL#anchor",
        "AAPL US",
        "../etc/passwd",
    ],
    ids=[
        "empty",
        "none",
        "int",
        "slash-path-traversal",
        "question-mark-injection",
        "ampersand-injection",
        "hash-injection",
        "space-in-middle",
        "path-traversal",
    ],
)
def test_sanitize_ticker_rejects(value):
    with pytest.raises(ToolError):
        sanitize_ticker(value)


@pytest.mark.xfail(reason="BUG-1: whitespace-only ticker passes guard before strip(), returns empty string")
def test_sanitize_ticker_whitespace_only_bug():
    """Whitespace-only input should raise ToolError but currently returns ''."""
    with pytest.raises(ToolError):
        sanitize_ticker("   ")


def test_sanitize_ticker_custom_param_name():
    """Error message includes custom param_name."""
    with pytest.raises(ToolError, match="symbol"):
        sanitize_ticker("", param_name="symbol")


# ---------------------------------------------------------------------------
# sanitize_exchange — mirrors sanitize_ticker behavior
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        ("US", "US"),
        ("  NASDAQ  ", "NASDAQ"),
        ("LSE", "LSE"),
    ],
)
def test_sanitize_exchange_valid(value, expected):
    assert sanitize_exchange(value) == expected


@pytest.mark.parametrize(
    "value",
    ["", None, 42, "US/UK", "US?x", "US&y", "US#z", "U S"],
    ids=["empty", "none", "int", "slash", "qmark", "amp", "hash", "space"],
)
def test_sanitize_exchange_rejects(value):
    with pytest.raises(ToolError):
        sanitize_exchange(value)


@pytest.mark.xfail(reason="BUG-1: whitespace-only exchange passes guard before strip()")
def test_sanitize_exchange_whitespace_only_bug():
    with pytest.raises(ToolError):
        sanitize_exchange("   ")


def test_sanitize_exchange_custom_param_name():
    with pytest.raises(ToolError, match="market"):
        sanitize_exchange("", param_name="market")


# ---------------------------------------------------------------------------
# _parse_to_datetime — numeric inputs
# ---------------------------------------------------------------------------


class TestParseDatetimeNumeric:
    def test_unix_seconds_int(self):
        dt = _parse_to_datetime(1694455200)
        assert dt is not None
        assert dt.year >= 2023

    def test_unix_milliseconds(self):
        dt = _parse_to_datetime(1694455200000)
        assert dt is not None
        assert dt.year >= 2023

    def test_unix_seconds_float(self):
        dt = _parse_to_datetime(1694455200.5)
        assert dt is not None

    def test_zero_returns_none(self):
        assert _parse_to_datetime(0) is None

    def test_negative_returns_none(self):
        assert _parse_to_datetime(-1) is None

    def test_non_string_non_numeric_returns_none(self):
        assert _parse_to_datetime([2024, 1, 1]) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _parse_to_datetime — string inputs
# ---------------------------------------------------------------------------


class TestParseDatetimeString:
    def test_iso_date(self):
        dt = _parse_to_datetime("2024-01-15")
        assert dt is not None
        assert dt.year == 2024 and dt.month == 1 and dt.day == 15

    def test_iso_with_time(self):
        dt = _parse_to_datetime("2024-01-15T10:30:00")
        assert dt is not None
        assert dt.hour == 10

    def test_iso_with_z(self):
        dt = _parse_to_datetime("2024-01-15T10:30:00Z")
        assert dt is not None

    def test_iso_with_offset(self):
        dt = _parse_to_datetime("2024-01-15T10:30:00+05:00")
        assert dt is not None

    def test_digit_string_unix(self):
        dt = _parse_to_datetime("1694455200")
        assert dt is not None
        assert dt.year >= 2023

    def test_digit_string_millis(self):
        dt = _parse_to_datetime("1694455200000")
        assert dt is not None

    def test_slash_ymd(self):
        dt = _parse_to_datetime("2024/01/15")
        assert dt is not None
        assert dt.day == 15

    def test_dot_ymd(self):
        dt = _parse_to_datetime("2024.01.15")
        assert dt is not None

    def test_month_name_mdy(self):
        dt = _parse_to_datetime("Jan 15, 2024")
        assert dt is not None
        assert dt.month == 1

    def test_month_name_dmy(self):
        dt = _parse_to_datetime("15 Jan 2024")
        assert dt is not None
        assert dt.day == 15

    def test_full_month_name(self):
        dt = _parse_to_datetime("January 15, 2024")
        assert dt is not None

    def test_empty_string(self):
        assert _parse_to_datetime("") is None

    def test_whitespace_only(self):
        assert _parse_to_datetime("   ") is None

    def test_garbage(self):
        assert _parse_to_datetime("not-a-date") is None

    def test_date_with_time_no_tz(self):
        dt = _parse_to_datetime("2024-01-15 14:30")
        assert dt is not None
        assert dt.hour == 14

    def test_date_with_full_time(self):
        dt = _parse_to_datetime("2024-01-15 14:30:45")
        assert dt is not None
        assert dt.second == 45


# ---------------------------------------------------------------------------
# BUG-2: Date format ambiguity — day-first wins over US month-first
# ---------------------------------------------------------------------------


class TestDateAmbiguity:
    def test_ambiguous_slash_day_first_wins(self):
        """'01/02/2024' → day-first format wins → Feb 1, not Jan 2.
        This documents current behavior (BUG-2). If changed, update this test."""
        result = format_date_ymd("01/02/2024")
        assert result == "2024-02-01"  # day-first: dd/mm/yyyy → Feb 1

    def test_ambiguous_dash_day_first_wins(self):
        result = format_date_ymd("01-02-2024")
        assert result == "2024-02-01"

    def test_unambiguous_high_day(self):
        """Day > 12 is unambiguous — must be dd/mm."""
        result = format_date_ymd("25/12/2024")
        assert result == "2024-12-25"


# ---------------------------------------------------------------------------
# _to_unix_seconds
# ---------------------------------------------------------------------------


class TestToUnixSeconds:
    def test_naive_datetime(self):
        from datetime import datetime, timezone

        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        ts = _to_unix_seconds(dt)
        assert isinstance(ts, int)
        assert ts > 0

    def test_aware_datetime(self):
        from datetime import datetime, timezone

        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        ts = _to_unix_seconds(dt)
        assert isinstance(ts, int)


# ---------------------------------------------------------------------------
# format_date
# ---------------------------------------------------------------------------


class TestFormatDate:
    def test_none_returns_none(self):
        assert format_date(None) is None

    def test_iso_to_default_ymd(self):
        assert format_date("2024-01-15") == "2024-01-15"

    def test_custom_output_format(self):
        result = format_date("2024-01-15", "%d/%m/%Y")
        assert result == "15/01/2024"

    def test_unix_timestamp(self):
        result = format_date(1704067200)  # 2024-01-01 00:00 UTC
        assert result is not None
        assert result.startswith("2024")

    def test_unparseable_returns_none(self):
        assert format_date("garbage") is None

    def test_empty_returns_none(self):
        assert format_date("") is None


# ---------------------------------------------------------------------------
# format_date_ymd
# ---------------------------------------------------------------------------


class TestFormatDateYmd:
    def test_none(self):
        assert format_date_ymd(None) is None

    def test_iso(self):
        assert format_date_ymd("2024-03-15") == "2024-03-15"

    def test_slash(self):
        assert format_date_ymd("2024/03/15") == "2024-03-15"

    def test_unix(self):
        result = format_date_ymd(1704067200)
        assert result is not None
        assert "2024" in result


# ---------------------------------------------------------------------------
# format_date_unix
# ---------------------------------------------------------------------------


class TestFormatDateUnix:
    def test_none(self):
        assert format_date_unix(None) is None

    def test_iso_string(self):
        result = format_date_unix("2024-01-01")
        assert result is not None
        assert isinstance(result, int)
        assert result > 0

    def test_passthrough_int(self):
        result = format_date_unix(1704067200)
        assert result is not None
        assert isinstance(result, int)

    def test_unparseable(self):
        assert format_date_unix("nope") is None

    def test_empty(self):
        assert format_date_unix("") is None
