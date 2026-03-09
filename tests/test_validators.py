"""Tests for app.validators — ticker, exchange, date validation."""

import pytest
from fastmcp.exceptions import ToolError

from app.validators import validate_date, validate_exchange, validate_ticker


class TestValidateTicker:
    def test_simple_ticker(self):
        assert validate_ticker("AAPL.US") == "AAPL.US"

    def test_crypto_ticker(self):
        assert validate_ticker("BTC-USD.CC") == "BTC-USD.CC"

    def test_forex_ticker(self):
        assert validate_ticker("EUR.FOREX") == "EUR.FOREX"

    def test_index_ticker(self):
        assert validate_ticker("GSPC.INDX") == "GSPC.INDX"

    def test_strips_whitespace(self):
        assert validate_ticker("  AAPL.US  ") == "AAPL.US"

    def test_underscore_allowed(self):
        assert validate_ticker("VTI_X.US") == "VTI_X.US"

    def test_empty_string_raises(self):
        with pytest.raises(ToolError, match="required"):
            validate_ticker("")

    def test_none_raises(self):
        with pytest.raises(ToolError, match="required"):
            validate_ticker(None)

    def test_invalid_chars_raises(self):
        with pytest.raises(ToolError, match="invalid characters"):
            validate_ticker("AAPL;DROP")

    def test_too_long_raises(self):
        with pytest.raises(ToolError, match="invalid characters"):
            validate_ticker("A" * 51)

    def test_spaces_in_middle_raises(self):
        with pytest.raises(ToolError, match="invalid characters"):
            validate_ticker("AA PL")

    def test_custom_param_name(self):
        with pytest.raises(ToolError, match="'symbol'"):
            validate_ticker("", param_name="symbol")


class TestValidateExchange:
    def test_valid_exchange(self):
        assert validate_exchange("US") == "US"

    def test_longer_code(self):
        assert validate_exchange("XETRA") == "XETRA"

    def test_numeric_code(self):
        assert validate_exchange("LSE2") == "LSE2"

    def test_strips_whitespace(self):
        assert validate_exchange("  US  ") == "US"

    def test_empty_raises(self):
        with pytest.raises(ToolError, match="required"):
            validate_exchange("")

    def test_none_raises(self):
        with pytest.raises(ToolError, match="required"):
            validate_exchange(None)

    def test_dots_rejected(self):
        with pytest.raises(ToolError, match="invalid characters"):
            validate_exchange("US.X")

    def test_hyphens_rejected(self):
        with pytest.raises(ToolError, match="invalid characters"):
            validate_exchange("US-X")

    def test_too_long_raises(self):
        with pytest.raises(ToolError, match="invalid characters"):
            validate_exchange("A" * 21)

    def test_custom_param_name(self):
        with pytest.raises(ToolError, match="'exchange'"):
            validate_exchange("", param_name="exchange")


class TestValidateDate:
    def test_none_is_valid(self):
        assert validate_date(None) is True

    def test_valid_date(self):
        assert validate_date("2026-01-15") is True

    def test_leap_day(self):
        assert validate_date("2024-02-29") is True

    def test_wrong_format_raises(self):
        with pytest.raises(ToolError, match="YYYY-MM-DD"):
            validate_date("01-15-2026")

    def test_slash_format_raises(self):
        with pytest.raises(ToolError, match="YYYY-MM-DD"):
            validate_date("2026/01/15")

    def test_invalid_month_raises(self):
        with pytest.raises(ToolError, match="not a valid date"):
            validate_date("2026-13-01")

    def test_invalid_day_raises(self):
        with pytest.raises(ToolError, match="not a valid date"):
            validate_date("2026-02-30")

    def test_not_a_leap_year_raises(self):
        with pytest.raises(ToolError, match="not a valid date"):
            validate_date("2025-02-29")

    def test_custom_param_name(self):
        with pytest.raises(ToolError, match="'start_date'"):
            validate_date("bad", param_name="start_date")
