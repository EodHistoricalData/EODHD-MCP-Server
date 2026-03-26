# tests/auto/test_api_client.py
"""Tests for app.api_client — token injection, backoff, make_request, retry,
rate limiting, token redaction, token resolution, HTTP methods."""

import asyncio
import time
from itertools import pairwise
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx
from app.api_client import (
    RETRY_DELAY_MAX,
    _backoff,
    _clear_connection_states,
    _ensure_api_token,
    _parse_retry_after,
    _redact_url,
    _resolve_eodhd_token_from_request,
    close_client,
    make_request,
    set_rate_limit,
)
from httpx import Response

# ---------------------------------------------------------------------------
# _redact_url  (TST-7)
# ---------------------------------------------------------------------------


class TestRedactUrl:
    def test_redacts_token(self):
        url = "https://eodhd.com/api/eod/AAPL.US?api_token=SECRET123&fmt=json"
        result = _redact_url(url)
        assert "SECRET123" not in result
        assert "api_token=***" in result
        assert "fmt=json" in result

    def test_no_token_unchanged(self):
        url = "https://eodhd.com/api/exchanges-list/?fmt=json"
        assert _redact_url(url) == url

    def test_multiple_tokens(self):
        url = "https://x.com?api_token=A&other=1&api_token=B"
        result = _redact_url(url)
        assert "api_token=A" not in result
        assert "api_token=B" not in result
        assert result.count("api_token=***") == 2


# ---------------------------------------------------------------------------
# _resolve_eodhd_token_from_request  (TST-6)
# ---------------------------------------------------------------------------


class TestResolveToken:
    def test_no_request_context_returns_none(self):
        """When get_http_request raises RuntimeError, returns None."""
        with patch("app.api_client.get_http_request", side_effect=RuntimeError):
            assert _resolve_eodhd_token_from_request() is None

    def test_unexpected_error_returns_none(self):
        with patch("app.api_client.get_http_request", side_effect=ValueError("boom")):
            assert _resolve_eodhd_token_from_request() is None

    def test_bearer_token(self):
        req = MagicMock()
        req.headers = {"authorization": "Bearer my_secret_token"}
        req.query_params = {}
        with patch("app.api_client.get_http_request", return_value=req):
            assert _resolve_eodhd_token_from_request() == "my_secret_token"

    def test_bearer_case_insensitive(self):
        req = MagicMock()
        req.headers = {"authorization": "bearer TOKEN123"}
        req.query_params = {}
        with patch("app.api_client.get_http_request", return_value=req):
            assert _resolve_eodhd_token_from_request() == "TOKEN123"

    def test_x_api_key_header(self):
        req = MagicMock()
        req.headers = {"x-api-key": "xkey123"}
        req.query_params = {}
        with patch("app.api_client.get_http_request", return_value=req):
            assert _resolve_eodhd_token_from_request() == "xkey123"

    def test_query_param_apikey(self):
        req = MagicMock()
        req.headers = {}
        req.query_params = {"apikey": "qp_key"}
        with patch("app.api_client.get_http_request", return_value=req):
            assert _resolve_eodhd_token_from_request() == "qp_key"

    def test_query_param_api_key(self):
        req = MagicMock()
        req.headers = {}
        req.query_params = {"api_key": "ak_val"}
        with patch("app.api_client.get_http_request", return_value=req):
            assert _resolve_eodhd_token_from_request() == "ak_val"

    def test_query_param_token(self):
        req = MagicMock()
        req.headers = {}
        req.query_params = {"token": "tok_val"}
        with patch("app.api_client.get_http_request", return_value=req):
            assert _resolve_eodhd_token_from_request() == "tok_val"

    def test_bearer_wins_over_xapi(self):
        """Priority: Bearer > X-API-Key."""
        req = MagicMock()
        req.headers = {"authorization": "Bearer winner", "x-api-key": "loser"}
        req.query_params = {}
        with patch("app.api_client.get_http_request", return_value=req):
            assert _resolve_eodhd_token_from_request() == "winner"

    def test_empty_bearer_falls_through(self):
        req = MagicMock()
        req.headers = {"authorization": "Bearer   ", "x-api-key": "fallback"}
        req.query_params = {}
        with patch("app.api_client.get_http_request", return_value=req):
            assert _resolve_eodhd_token_from_request() == "fallback"


# ---------------------------------------------------------------------------
# _ensure_api_token
# ---------------------------------------------------------------------------


class TestEnsureApiToken:
    """_ensure_api_token appends api_token from env when missing."""

    def test_uses_latest_env_token_after_import(self, monkeypatch):
        monkeypatch.setenv("EODHD_API_KEY", "cli_override_key")
        url = "https://eodhd.com/api/eod/AAPL.US"
        result = _ensure_api_token(url)
        assert result.endswith("?api_token=cli_override_key")

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
# _parse_retry_after (RFC 7231 §7.1.3)
# ---------------------------------------------------------------------------


class TestParseRetryAfter:
    def test_integer_seconds(self):
        assert _parse_retry_after("5") == 5

    def test_none_returns_default(self):
        assert _parse_retry_after(None) == 60

    def test_empty_returns_default(self):
        assert _parse_retry_after("") == 60

    def test_http_date(self):
        """RFC 7231 HTTP-date format should be parsed into a delay."""
        import email.utils
        from datetime import datetime, timezone, timedelta

        future = datetime.now(timezone.utc) + timedelta(seconds=30)
        http_date = email.utils.format_datetime(future)
        result = _parse_retry_after(http_date)
        assert 25 <= result <= 35  # allow clock skew

    def test_garbage_returns_default(self):
        assert _parse_retry_after("not-a-number-or-date") == 60

    def test_negative_clamped_to_zero(self):
        assert _parse_retry_after("-10") == 0

    def test_huge_value_capped_at_3600(self):
        assert _parse_retry_after("999999") == 3600

    def test_zero(self):
        assert _parse_retry_after("0") == 0


# ---------------------------------------------------------------------------
# set_rate_limit
# ---------------------------------------------------------------------------


class TestSetRateLimit:
    def test_sets_positive(self):
        set_rate_limit(0.5)
        import app.api_client as ac

        assert ac._rate_limiter.delay == 0.5
        assert ac._rate_limiter.enabled is True
        # restore default (disabled)
        set_rate_limit(0.0)

    def test_negative_clamped_to_zero(self):
        set_rate_limit(-1.0)
        import app.api_client as ac

        assert ac._rate_limiter.delay == 0.0
        assert ac._rate_limiter.enabled is False

    def test_disabled_by_default(self):
        import app.api_client as ac

        # Default singleton should be disabled unless env var is set
        assert ac._rate_limiter.delay == 0.0
        assert ac._rate_limiter.enabled is False


# ---------------------------------------------------------------------------
# close_client
# ---------------------------------------------------------------------------


class TestCloseClient:
    @pytest.mark.asyncio
    async def test_close_client_calls_aclose(self):
        mock_client = AsyncMock()
        with patch("app.api_client._http_client", mock_client):
            await close_client()
        mock_client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_client_without_client_is_noop(self, monkeypatch):
        import app.api_client as ac

        monkeypatch.setattr(ac, "_http_client", None)
        await close_client()
        assert ac._http_client is None


# ---------------------------------------------------------------------------
# make_request — existing auto
# ---------------------------------------------------------------------------


class TestMakeRequest:
    """Integration-ish auto for make_request using respx mocks."""

    @pytest.mark.asyncio
    async def test_make_request_lazily_creates_client(self, monkeypatch):
        import app.api_client as ac

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            return_value=Response(
                200,
                json={"close": 150.0},
                request=httpx.Request("GET", "https://eodhd.com/api/eod/AAPL.US"),
            )
        )
        mock_client.aclose = AsyncMock()

        monkeypatch.setattr(ac, "_http_client", None)
        _clear_connection_states()

        try:
            with patch("app.api_client.httpx.AsyncClient", return_value=mock_client) as mock_ctor:
                result = await make_request("https://eodhd.com/api/eod/AAPL.US")
            assert result == {"close": 150.0}
            mock_ctor.assert_called_once()
            assert ac._http_client is mock_client
        finally:
            _clear_connection_states()
            await close_client()


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
            return_value=Response(
                403,
                json={"code": "FORBIDDEN_PLAN", "errorMessage": "Upgrade required for this endpoint."},
            )
        )
        result = await make_request("https://eodhd.com/api/eod/BAD")
        assert result is not None
        assert "error" in result
        assert result["status_code"] == 403
        assert result["error"] == "EODHD API request failed with 403 Forbidden."
        assert result["error_code"] == "FORBIDDEN_PLAN"
        assert result["upstream_message"] == "Upgrade required for this endpoint."
        assert "api_token=" not in result["error"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_429_without_retry_returns_error(self):
        respx.get(url__startswith="https://eodhd.com/api/limited").mock(
            return_value=Response(429, text="Too Many Requests", headers={"Retry-After": "5"})
        )
        with patch("app.api_client.asyncio.sleep", new_callable=AsyncMock):
            result = await make_request("https://eodhd.com/api/limited", retry_enabled=False)
        assert result is not None
        assert result["status_code"] == 429
        assert result["retry_after"] == 5
        assert result["upstream_message"] == "Retry after 5 seconds."
        assert "rate limit exceeded" in result["error"].lower()

    @pytest.mark.asyncio
    @respx.mock
    async def test_5xx_no_retry(self):
        """With retry_enabled=False, a 5xx should be tried only once."""
        route = respx.get(url__startswith="https://eodhd.com/api/fail").mock(
            return_value=Response(502, text="Bad Gateway")
        )
        result = await make_request("https://eodhd.com/api/fail", retry_enabled=False)
        assert result is not None
        assert "error" in result
        assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_requests_same_token_are_rate_limited(self):
        call_times: list[float] = []
        mock_client = MagicMock()
        urls = [
            "https://eodhd.com/api/eod/AAPL.US?api_token=shared-key",
            "https://eodhd.com/api/eod/MSFT.US?api_token=shared-key",
            "https://eodhd.com/api/eod/GOOGL.US?api_token=shared-key",
        ]

        async def fake_get(url, headers=None, timeout=None):
            call_times.append(time.monotonic())
            return Response(200, json={"ok": True}, request=httpx.Request("GET", url))

        mock_client.get = AsyncMock(side_effect=fake_get)

        _clear_connection_states()
        set_rate_limit(0.05)  # enable rate limiting for this test

        try:
            with patch("app.api_client._http_client", mock_client):
                results = await asyncio.gather(*(make_request(url) for url in urls))
        finally:
            set_rate_limit(0.0)  # restore default (disabled)
            _clear_connection_states()

        assert results == [{"ok": True}, {"ok": True}, {"ok": True}]
        assert len(call_times) == 3
        gaps = [later - earlier for earlier, later in pairwise(call_times)]
        assert all(gap >= 0.045 for gap in gaps)

    @pytest.mark.asyncio
    async def test_concurrent_requests_different_tokens_do_not_share_rate_limit(self):
        call_times: dict[str, float] = {}
        mock_client = MagicMock()
        url_a = "https://eodhd.com/api/eod/AAPL.US?api_token=token-a"
        url_b = "https://eodhd.com/api/eod/MSFT.US?api_token=token-b"

        async def fake_get(url, headers=None, timeout=None):
            call_times[url] = time.monotonic()
            return Response(200, json={"ok": True}, request=httpx.Request("GET", url))

        mock_client.get = AsyncMock(side_effect=fake_get)

        _clear_connection_states()
        set_rate_limit(0.05)  # enable rate limiting for this test

        try:
            with patch("app.api_client._http_client", mock_client):
                results = await asyncio.gather(make_request(url_a), make_request(url_b))
        finally:
            set_rate_limit(0.0)  # restore default (disabled)
            _clear_connection_states()

        assert results == [{"ok": True}, {"ok": True}]
        assert len(call_times) == 2
        assert abs(call_times[url_a] - call_times[url_b]) < 0.04

    @pytest.mark.asyncio
    async def test_unsupported_method(self):
        result = await make_request("https://eodhd.com/api/eod/AAPL.US", method="PATCH")
        assert result is not None
        assert "error" in result
        assert "Unsupported HTTP method" in result["error"]


# ---------------------------------------------------------------------------
# make_request — HTTP methods (POST, PUT, DELETE)
# ---------------------------------------------------------------------------


class TestMakeRequestMethods:
    @pytest.mark.asyncio
    @respx.mock
    async def test_post_with_json(self):
        respx.post(url__startswith="https://eodhd.com/api/test").mock(
            return_value=Response(200, json={"created": True})
        )
        result = await make_request(
            "https://eodhd.com/api/test",
            method="POST",
            json_body={"data": "value"},
        )
        assert result == {"created": True}

    @pytest.mark.asyncio
    @respx.mock
    async def test_put_request(self):
        respx.put(url__startswith="https://eodhd.com/api/test").mock(return_value=Response(200, json={"updated": True}))
        result = await make_request("https://eodhd.com/api/test", method="PUT", json_body={"x": 1})
        assert result == {"updated": True}

    @pytest.mark.asyncio
    @respx.mock
    async def test_delete_request(self):
        respx.delete(url__startswith="https://eodhd.com/api/test").mock(
            return_value=Response(200, json={"deleted": True})
        )
        result = await make_request("https://eodhd.com/api/test", method="DELETE")
        assert result == {"deleted": True}

    @pytest.mark.asyncio
    async def test_method_case_insensitive(self):
        """'get' should work same as 'GET'."""
        with respx.mock:
            respx.get(url__startswith="https://eodhd.com/api/test").mock(return_value=Response(200, json={"ok": True}))
            result = await make_request("https://eodhd.com/api/test", method="get")
        assert result == {"ok": True}


# ---------------------------------------------------------------------------
# make_request — non-JSON response
# ---------------------------------------------------------------------------


class TestMakeRequestNonJson:
    @pytest.mark.asyncio
    @respx.mock
    async def test_non_json_200(self):
        respx.get(url__startswith="https://eodhd.com/api/csv").mock(
            return_value=Response(200, text="col1,col2\n1,2", headers={"content-type": "text/csv"})
        )
        result = await make_request("https://eodhd.com/api/csv")
        assert result is not None
        assert "error" in result
        assert result["error"] == "Response is not valid JSON."
        assert result["content_type"] == "text/csv"

    @pytest.mark.asyncio
    @respx.mock
    async def test_long_non_json_truncated(self):
        long_text = "x" * 3000
        respx.get(url__startswith="https://eodhd.com/api/big").mock(
            return_value=Response(200, text=long_text, headers={"content-type": "text/html"})
        )
        result = await make_request("https://eodhd.com/api/big")
        assert result is not None
        assert len(result["text"]) <= 2001  # 2000 + "…"


# ---------------------------------------------------------------------------
# make_request — retry logic (TST-4)
# ---------------------------------------------------------------------------


class TestMakeRequestRetry:
    @pytest.mark.asyncio
    @respx.mock
    async def test_5xx_retry_exhausted(self):
        """All retries fail with 502 → error returned, 4 attempts total."""
        route = respx.get(url__startswith="https://eodhd.com/api/fail").mock(
            return_value=Response(502, text="Bad Gateway")
        )
        with patch("app.api_client.asyncio.sleep", new_callable=AsyncMock):
            result = await make_request("https://eodhd.com/api/fail", retry_enabled=True)
        assert result is not None
        assert "error" in result
        assert route.call_count == 4  # 1 + 3 retries

    @pytest.mark.asyncio
    async def test_5xx_retry_succeeds_second(self):
        """502 first, 200 second → success."""
        with respx.mock:
            route = respx.get(url__startswith="https://eodhd.com/api/flaky").mock(
                side_effect=[
                    Response(502, text="Bad Gateway"),
                    Response(200, json={"ok": True}),
                ]
            )
            with patch("app.api_client.asyncio.sleep", new_callable=AsyncMock):
                result = await make_request("https://eodhd.com/api/flaky", retry_enabled=True)
        assert result == {"ok": True}
        assert route.call_count == 2

    @pytest.mark.asyncio
    @respx.mock
    async def test_429_retry_after_header(self):
        """429 with Retry-After header, then 200."""
        respx.get(url__startswith="https://eodhd.com/api/limited").mock(
            side_effect=[
                Response(429, headers={"Retry-After": "1"}),
                Response(200, json={"ok": True}),
            ]
        )
        with patch("app.api_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await make_request("https://eodhd.com/api/limited", retry_enabled=True)
        assert result == {"ok": True}
        # asyncio.sleep called at least once for Retry-After
        sleep_calls = [c.args[0] for c in mock_sleep.await_args_list if c.args]
        assert any(s >= 1 for s in sleep_calls)

    @pytest.mark.asyncio
    async def test_timeout_with_retry(self):
        """TimeoutException → retries, then 200."""
        with respx.mock:
            route = respx.get(url__startswith="https://eodhd.com/api/slow").mock(
                side_effect=[
                    httpx.TimeoutException("timeout"),
                    Response(200, json={"recovered": True}),
                ]
            )
            with patch("app.api_client.asyncio.sleep", new_callable=AsyncMock):
                result = await make_request("https://eodhd.com/api/slow", retry_enabled=True)
        assert result == {"recovered": True}
        assert route.call_count == 2

    @pytest.mark.asyncio
    async def test_network_error_returns_error(self):
        """ConnectError → error dict."""
        with respx.mock:
            respx.get(url__startswith="https://eodhd.com/api/down").mock(side_effect=httpx.ConnectError("refused"))
            with patch("app.api_client.asyncio.sleep", new_callable=AsyncMock):
                result = await make_request("https://eodhd.com/api/down", retry_enabled=False)
        assert result is not None
        assert "error" in result
