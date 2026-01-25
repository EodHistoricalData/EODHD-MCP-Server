# tests/test_export.py
"""Tests for app/export.py module."""

import json
import pytest
from app.export import (
    to_csv,
    to_json,
    export_price_data,
    export_fundamentals,
    export_screener_results
)


class TestToCsv:
    """Tests for to_csv() function."""

    def test_basic_conversion(self):
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25}
        ]
        result = to_csv(data)
        assert "name,age" in result
        assert "Alice,30" in result
        assert "Bob,25" in result

    def test_empty_data(self):
        result = to_csv([])
        assert result == ""

    def test_with_columns(self):
        data = [
            {"name": "Alice", "age": 30, "city": "NYC"},
            {"name": "Bob", "age": 25, "city": "LA"}
        ]
        result = to_csv(data, columns=["name", "city"])
        assert "name,city" in result
        assert "age" not in result.split("\n")[0]  # age not in header

    def test_utf8_bom(self):
        data = [{"name": "Test"}]
        result = to_csv(data, include_bom=True)
        assert result.startswith('\ufeff')

    def test_nested_data_to_json(self):
        data = [
            {"name": "Test", "data": {"key": "value"}}
        ]
        result = to_csv(data)
        # CSV escapes quotes, so check for the escaped version
        assert "key" in result and "value" in result


class TestToJson:
    """Tests for to_json() function."""

    def test_basic_conversion(self):
        data = {"key": "value"}
        result = to_json(data, include_metadata=False)
        parsed = json.loads(result)
        assert parsed == {"key": "value"}

    def test_with_metadata(self):
        data = [1, 2, 3]
        result = to_json(data, include_metadata=True)
        parsed = json.loads(result)
        assert "metadata" in parsed
        assert "data" in parsed
        assert parsed["metadata"]["record_count"] == 3
        assert "exported_at" in parsed["metadata"]

    def test_list_data(self):
        data = [{"a": 1}, {"a": 2}]
        result = to_json(data)
        parsed = json.loads(result)
        assert parsed["data"] == data


class TestExportPriceData:
    """Tests for export_price_data() function."""

    def test_json_format(self):
        data = [
            {"date": "2024-01-15", "open": 100, "high": 105, "low": 99, "close": 104, "volume": 1000}
        ]
        result = export_price_data(data, format="json", ticker="AAPL.US")
        assert result["format"] == "json"
        assert result["ticker"] == "AAPL.US"
        assert result["rows"] == 1

    def test_csv_format(self):
        data = [
            {"date": "2024-01-15", "open": 100, "high": 105, "low": 99, "close": 104, "volume": 1000}
        ]
        result = export_price_data(data, format="csv", ticker="AAPL.US")
        assert result["format"] == "csv"
        assert "date" in result["content"]


class TestExportFundamentals:
    """Tests for export_fundamentals() function."""

    def test_json_format(self):
        data = {
            "General": {"Name": "Apple Inc.", "Sector": "Technology"},
            "Highlights": {"MarketCap": 3000000000000}
        }
        result = export_fundamentals(data, format="json")
        assert result["format"] == "json"
        assert "General" in result["sections"]

    def test_with_sections_filter(self):
        data = {
            "General": {"Name": "Apple Inc."},
            "Highlights": {"MarketCap": 3000000000000},
            "Valuation": {"PE": 28}
        }
        result = export_fundamentals(data, sections=["General"], format="json")
        assert "General" in result["sections"]
        assert "Valuation" not in result["sections"]


class TestExportScreenerResults:
    """Tests for export_screener_results() function."""

    def test_json_format(self):
        data = [
            {"code": "AAPL", "name": "Apple", "market_capitalization": 3000000000000}
        ]
        result = export_screener_results(data, format="json")
        assert result["format"] == "json"
        assert result["rows"] == 1

    def test_csv_format(self):
        data = [
            {"code": "AAPL", "name": "Apple", "market_capitalization": 3000000000000}
        ]
        result = export_screener_results(data, format="csv")
        assert result["format"] == "csv"
        assert "content" in result

    def test_custom_columns(self):
        data = [
            {"code": "AAPL", "name": "Apple", "extra": "data"}
        ]
        result = export_screener_results(data, format="json", columns=["code", "name"])
        assert result["columns"] == ["code", "name"]
