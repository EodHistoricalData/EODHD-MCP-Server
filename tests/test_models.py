# tests/test_models.py
"""Tests for app/models.py module."""

import pytest
from pydantic import ValidationError
from app.models import (
    StockPrice,
    LiveQuote,
    IntradayBar,
    CompanyGeneral,
    Highlights,
    NewsArticle,
    EarningsEvent,
    Exchange,
    Ticker,
    APIResponse
)


class TestStockPrice:
    """Tests for StockPrice model."""

    def test_valid_stock_price(self):
        data = {
            "date": "2024-01-15",
            "open": 185.0,
            "high": 186.5,
            "low": 184.0,
            "close": 185.5,
            "volume": 50000000
        }
        price = StockPrice(**data)
        assert price.date == "2024-01-15"
        assert price.close == 185.5
        assert price.volume == 50000000

    def test_with_adjusted_close(self):
        data = {
            "date": "2024-01-15",
            "open": 185.0,
            "high": 186.5,
            "low": 184.0,
            "close": 185.5,
            "adjusted_close": 185.3,
            "volume": 50000000
        }
        price = StockPrice(**data)
        assert price.adjusted_close == 185.3


class TestLiveQuote:
    """Tests for LiveQuote model."""

    def test_valid_live_quote(self):
        data = {
            "code": "AAPL",
            "timestamp": 1704067200,
            "gmtoffset": 0,
            "open": 185.0,
            "high": 186.5,
            "low": 184.0,
            "close": 185.5,
            "volume": 50000000
        }
        quote = LiveQuote(**data)
        assert quote.code == "AAPL"
        assert quote.timestamp == 1704067200

    def test_with_optional_fields(self):
        data = {
            "code": "AAPL",
            "timestamp": 1704067200,
            "gmtoffset": 0,
            "open": 185.0,
            "high": 186.5,
            "low": 184.0,
            "close": 185.5,
            "volume": 50000000,
            "change": 1.5,
            "change_p": 0.82
        }
        quote = LiveQuote(**data)
        assert quote.change == 1.5
        assert quote.change_p == 0.82


class TestIntradayBar:
    """Tests for IntradayBar model."""

    def test_valid_intraday_bar(self):
        data = {
            "timestamp": 1704067200,
            "gmtoffset": 0,
            "datetime": "2024-01-01 10:00:00",
            "open": 185.0,
            "high": 185.5,
            "low": 184.8,
            "close": 185.2,
            "volume": 1000000
        }
        bar = IntradayBar(**data)
        assert bar.datetime == "2024-01-01 10:00:00"


class TestCompanyGeneral:
    """Tests for CompanyGeneral model."""

    def test_valid_company_general(self):
        data = {
            "Code": "AAPL",
            "Name": "Apple Inc.",
            "Exchange": "NASDAQ",
            "Sector": "Technology",
            "Industry": "Consumer Electronics"
        }
        company = CompanyGeneral(**data)
        assert company.Code == "AAPL"
        assert company.Name == "Apple Inc."

    def test_with_all_fields(self):
        data = {
            "Code": "AAPL",
            "Type": "Common Stock",
            "Name": "Apple Inc.",
            "Exchange": "NASDAQ",
            "CurrencyCode": "USD",
            "CountryName": "USA",
            "ISIN": "US0378331005",
            "Sector": "Technology",
            "Industry": "Consumer Electronics",
            "FullTimeEmployees": 164000,
            "WebURL": "https://www.apple.com"
        }
        company = CompanyGeneral(**data)
        assert company.ISIN == "US0378331005"
        assert company.FullTimeEmployees == 164000


class TestHighlights:
    """Tests for Highlights model."""

    def test_valid_highlights(self):
        data = {
            "MarketCapitalization": 3000000000000,
            "PERatio": 28.5,
            "DividendYield": 0.005,
            "EarningsShare": 6.5
        }
        highlights = Highlights(**data)
        assert highlights.MarketCapitalization == 3000000000000
        assert highlights.PERatio == 28.5


class TestNewsArticle:
    """Tests for NewsArticle model."""

    def test_valid_news_article(self):
        data = {
            "date": "2024-01-15 10:30:00",
            "title": "Apple Announces New Product"
        }
        article = NewsArticle(**data)
        assert article.title == "Apple Announces New Product"

    def test_with_all_fields(self):
        data = {
            "date": "2024-01-15 10:30:00",
            "title": "Apple Announces New Product",
            "content": "Full article content...",
            "link": "https://example.com/article",
            "symbols": ["AAPL"],
            "tags": ["technology", "announcement"]
        }
        article = NewsArticle(**data)
        assert "AAPL" in article.symbols


class TestExchange:
    """Tests for Exchange model."""

    def test_valid_exchange(self):
        data = {
            "Name": "NASDAQ",
            "Code": "US"
        }
        exchange = Exchange(**data)
        assert exchange.Name == "NASDAQ"
        assert exchange.Code == "US"


class TestTicker:
    """Tests for Ticker model."""

    def test_valid_ticker(self):
        data = {
            "Code": "AAPL",
            "Name": "Apple Inc."
        }
        ticker = Ticker(**data)
        assert ticker.Code == "AAPL"


class TestAPIResponse:
    """Tests for APIResponse model."""

    def test_with_data(self):
        response = APIResponse(data={"key": "value"})
        assert response.data == {"key": "value"}
        assert response.error is None

    def test_with_error(self):
        response = APIResponse(error="Something went wrong")
        assert response.error == "Something went wrong"

    def test_with_meta(self):
        response = APIResponse(data=[1, 2, 3], meta={"count": 3})
        assert response.meta["count"] == 3
