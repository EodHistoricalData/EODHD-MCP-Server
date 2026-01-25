# tests/test_batch.py
"""Tests for app/batch.py module."""

import pytest
from unittest.mock import AsyncMock, patch
from app.batch import (
    BatchProcessor,
    batch_quotes,
    batch_eod,
    batch_fundamentals,
    compare_symbols
)


class TestBatchProcessor:
    """Tests for BatchProcessor class."""

    def test_init(self):
        processor = BatchProcessor(max_concurrent=5, delay_between=0.05)
        assert processor.max_concurrent == 5
        assert processor.delay_between == 0.05

    @pytest.mark.asyncio
    async def test_process_with_mock(self):
        processor = BatchProcessor(max_concurrent=2, delay_between=0.01)

        with patch('app.batch.make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"code": "AAPL", "price": 185.0}

            items = [{"id": "AAPL.US"}, {"id": "MSFT.US"}]
            result = await processor.process(
                items,
                lambda item: f"https://api.example.com/{item['id']}"
            )

            assert result["count"] == 2
            assert result["total"] == 2
            assert "AAPL.US" in result["results"]
            assert "MSFT.US" in result["results"]


class TestBatchFunctions:
    """Tests for batch helper functions."""

    @pytest.mark.asyncio
    async def test_batch_quotes_with_mock(self):
        with patch('app.batch.make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"code": "AAPL", "close": 185.0}

            result = await batch_quotes(["AAPL.US", "MSFT.US"])

            assert "results" in result
            assert "count" in result

    @pytest.mark.asyncio
    async def test_batch_eod_with_mock(self):
        with patch('app.batch.make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = [{"date": "2024-01-15", "close": 185.0}]

            result = await batch_eod(["AAPL.US"], date="2024-01-15")

            assert "results" in result

    @pytest.mark.asyncio
    async def test_batch_fundamentals_with_mock(self):
        with patch('app.batch.make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"General": {"Name": "Apple"}}

            result = await batch_fundamentals(["AAPL.US"])

            assert "results" in result

    @pytest.mark.asyncio
    async def test_compare_symbols_with_mock(self):
        with patch('app.batch.make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "General": {"Name": "Apple"},
                "Highlights": {"MarketCapitalization": 3000000000000}
            }

            result = await compare_symbols(["AAPL.US", "MSFT.US"])

            assert "results" in result
            assert "comparison" in result


class TestBatchErrorHandling:
    """Tests for batch error handling."""

    @pytest.mark.asyncio
    async def test_handles_api_errors(self):
        with patch('app.batch.make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"error": "API error"}

            result = await batch_quotes(["INVALID.XX"])

            assert result["count"] == 0
            assert result["errors"] is not None

    @pytest.mark.asyncio
    async def test_handles_none_response(self):
        with patch('app.batch.make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = None

            result = await batch_quotes(["AAPL.US"])

            assert result["count"] == 0
