# tests/conftest.py
"""
Pytest configuration and fixtures for EODHD MCP Server tests.
"""

import os
import pytest
import asyncio

# Set test API key
os.environ.setdefault("EODHD_API_KEY", "demo")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def api_key():
    """Return the API key used for testing."""
    return os.environ.get("EODHD_API_KEY", "demo")


@pytest.fixture
def sample_ticker():
    """Return a sample ticker for testing."""
    return "AAPL.US"


@pytest.fixture
def sample_exchange():
    """Return a sample exchange for testing."""
    return "US"


@pytest.fixture
def sample_date_range():
    """Return a sample date range for testing."""
    return {
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
    }


@pytest.fixture
def mock_api_response():
    """Return a mock API response for testing."""
    return {
        "code": "AAPL",
        "timestamp": 1704067200,
        "open": 185.0,
        "high": 186.5,
        "low": 184.0,
        "close": 185.5,
        "volume": 50000000
    }


@pytest.fixture
def mock_eod_data():
    """Return mock EOD data for testing."""
    return [
        {
            "date": "2024-01-15",
            "open": 185.0,
            "high": 186.5,
            "low": 184.0,
            "close": 185.5,
            "adjusted_close": 185.5,
            "volume": 50000000
        },
        {
            "date": "2024-01-14",
            "open": 184.0,
            "high": 185.0,
            "low": 183.0,
            "close": 184.5,
            "adjusted_close": 184.5,
            "volume": 45000000
        }
    ]
