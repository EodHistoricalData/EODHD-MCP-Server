"""Tests for app.api_client — token injection, backoff, make_request."""

import pytest
import respx
from httpx import Response

from app.api_client import _ensure_api_token, _backoff, make_request, RETRY_DELAY_MAX


# ---------------------------------------------------------------------------
# _ensure_api_token
# ---------------------------------------------------------------------------

class TestEnsureApiToken:
    """_ensure_api_token appends api_token from env when missing."""

    def test_adds_token_no_query_string(self):
        url = "https://eodhd.com/api/eod/AAPL.US"
        result = _ensure_api_token(url)
        assert "?api_token=" in result

    def test_adds_token_existing_query_string(self):
        url = "https://eodhd.com/api/eod/AAPL.US?fmt=json"
        result = _ensure_api_token(url)
        assert "&api_token=" in result
        assert result.startswith("https://eodhd.com/api/eod/AAPL.US?fmt=json&")

    def test_skips_if_api_token_present(self):
        url = "https://eodhd.com/api/eod/AAPL.US?api_token=MY_KEY"
        result = _ensure_api_token(url)
        assert result == url  # unchanged


# ---------------------------------------------------------------------------
# _backoff
# ---------------------------------------------------------------------------

class TestBackoff:
    """Exponential backoff: base * 2^attempt, capped at RETRY_DELAY_MAX."""

    def test_exponential_delays(self):
        assert _backoff(0) == pytest.approx(1.0)
        assert _backoff(1) == pytest.approx(2.0)
        assert _backoff(2) == pytest.approx(4.0)

    def test_capped_at_max(self):
        # 2^10 * 1.0 = 1024, must be capped
        assert _backoff(10) == pytest.approx(RETRY_DELAY_MAX)
        assert _backoff(100) == pytest.approx(RETRY_DELAY_MAX)


# ---------------------------------------------------------------------------
# make_request
# ---------------------------------------------------------------------------

class TestMakeRequest:
    """Integration-ish tests for make_request using respx mocks."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success_json(self):
        respx.get(url__startswith="https://eodhd.com/api/eod/AAPL.US").mock(
            return_value=Response(200, json={"close": 150.0})
        )
        result = await make_request("https://eodhd.com/api/eod/AAPL.US")
        assert result == {"close": 150.0}

    @pytest.mark.asyncio
    @respx.mock
    async def test_4xx_returns_error(self):
        respx.get(url__startswith="https://eodhd.com/api/eod/BAD").mock(
            return_value=Response(403, text="Forbidden")
        )
        result = await make_request("https://eodhd.com/api/eod/BAD")
        assert result is not None
        assert "error" in result
        assert result["status_code"] == 403

    @pytest.mark.asyncio
    @respx.mock
    async def test_5xx_no_retry(self):
        """With retry_enabled=False, a 5xx should be tried only once."""
        route = respx.get(url__startswith="https://eodhd.com/api/fail").mock(
            return_value=Response(502, text="Bad Gateway")
        )
        result = await make_request(
            "https://eodhd.com/api/fail", retry_enabled=False
        )
        assert result is not None
        assert "error" in result
        assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_unsupported_method(self):
        result = await make_request(
            "https://eodhd.com/api/eod/AAPL.US", method="PATCH"
        )
        assert result is not None
        assert "error" in result
        assert "Unsupported HTTP method" in result["error"]
