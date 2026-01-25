# tests/test_utils.py
"""Tests for app/utils.py module."""

import json
import pytest
from app.utils import (
    err,
    valid_date,
    validate_date_range,
    validate_ticker,
    validate_exchange,
    normalize_list_param,
    truncate,
    format_response
)


class TestErr:
    """Tests for err() function."""

    def test_returns_json_error(self):
        result = err("Something went wrong")
        parsed = json.loads(result)
        assert parsed == {"error": "Something went wrong"}

    def test_formats_with_indent(self):
        result = err("Test error")
        assert "  " in result  # Has indentation


class TestValidDate:
    """Tests for valid_date() function."""

    def test_valid_date_format(self):
        assert valid_date("2024-01-15") is True
        assert valid_date("2023-12-31") is True

    def test_invalid_date_format(self):
        assert valid_date("01-15-2024") is False
        assert valid_date("2024/01/15") is False
        assert valid_date("20240115") is False

    def test_invalid_date_values(self):
        assert valid_date("2024-13-01") is False  # Invalid month
        assert valid_date("2024-02-30") is False  # Invalid day

    def test_non_string_input(self):
        assert valid_date(None) is False
        assert valid_date(123) is False
        assert valid_date(["2024-01-15"]) is False


class TestValidateDateRange:
    """Tests for validate_date_range() function."""

    def test_valid_date_range(self):
        assert validate_date_range("2024-01-01", "2024-01-31") is None

    def test_none_dates(self):
        assert validate_date_range(None, None) is None
        assert validate_date_range("2024-01-01", None) is None
        assert validate_date_range(None, "2024-01-31") is None

    def test_invalid_start_date(self):
        result = validate_date_range("invalid", "2024-01-31")
        assert "start_date" in result

    def test_invalid_end_date(self):
        result = validate_date_range("2024-01-01", "invalid")
        assert "end_date" in result

    def test_start_after_end(self):
        result = validate_date_range("2024-02-01", "2024-01-01")
        assert "cannot be after" in result


class TestValidateTicker:
    """Tests for validate_ticker() function."""

    def test_valid_ticker(self):
        assert validate_ticker("AAPL.US") is None
        assert validate_ticker("MSFT") is None

    def test_empty_ticker(self):
        result = validate_ticker("")
        assert "required" in result

    def test_none_ticker(self):
        result = validate_ticker(None)
        assert "required" in result


class TestValidateExchange:
    """Tests for validate_exchange() function."""

    def test_valid_exchange(self):
        assert validate_exchange("US") is None
        assert validate_exchange("LSE") is None

    def test_empty_exchange(self):
        result = validate_exchange("")
        assert "required" in result


class TestNormalizeListParam:
    """Tests for normalize_list_param() function."""

    def test_none_returns_empty_list(self):
        assert normalize_list_param(None) == []

    def test_string_comma_separated(self):
        result = normalize_list_param("AAPL,MSFT,GOOGL")
        assert result == ["AAPL", "MSFT", "GOOGL"]

    def test_string_with_spaces(self):
        result = normalize_list_param("AAPL, MSFT, GOOGL")
        assert result == ["AAPL", "MSFT", "GOOGL"]

    def test_list_input(self):
        result = normalize_list_param(["AAPL", "MSFT"])
        assert result == ["AAPL", "MSFT"]

    def test_empty_string(self):
        assert normalize_list_param("") == []


class TestTruncate:
    """Tests for truncate() function."""

    def test_short_string_unchanged(self):
        assert truncate("hello", 10) == "hello"

    def test_long_string_truncated(self):
        result = truncate("hello world", 8)
        assert result == "hello..."
        assert len(result) == 8

    def test_custom_suffix(self):
        result = truncate("hello world", 9, suffix="~")
        assert result == "hello wo~"

    def test_none_input(self):
        assert truncate(None, 10) is None

    def test_empty_string(self):
        assert truncate("", 10) == ""


class TestFormatResponse:
    """Tests for format_response() function."""

    def test_dict_response(self):
        data = {"key": "value"}
        result = format_response(data)
        parsed = json.loads(result)
        assert parsed == {"key": "value"}

    def test_list_response(self):
        data = [1, 2, 3]
        result = format_response(data)
        parsed = json.loads(result)
        assert parsed == [1, 2, 3]

    def test_none_response(self):
        result = format_response(None)
        parsed = json.loads(result)
        assert "error" in parsed

    def test_error_response(self):
        data = {"error": "Something failed"}
        result = format_response(data)
        parsed = json.loads(result)
        assert parsed == {"error": "Something failed"}
