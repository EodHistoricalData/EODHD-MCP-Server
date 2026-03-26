# app/api_client.py
import asyncio
import email.utils
import logging
import re
import time
from http import HTTPStatus
from typing import Any, Literal
from urllib.parse import parse_qs, urlsplit

import httpx
from fastmcp.server.dependencies import get_http_request

from .config import EODHD_RATE_LIMIT_DELAY, EODHD_RETRY_ENABLED, get_api_key

logger = logging.getLogger("eodhd-mcp.api_client")

# Shared HTTP client — created lazily inside a running event loop
_http_client: httpx.AsyncClient | None = None
_http_client_lock: asyncio.Lock | None = None


def _get_client_lock() -> asyncio.Lock:
    """Return (and lazily create) the asyncio.Lock for client init.

    asyncio.Lock must be created inside a running event loop, so we create it
    on first access and recreate if the loop changes (e.g. between tests).
    """
    global _http_client_lock
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — return a fresh lock (caller is likely in tests)
        _http_client_lock = asyncio.Lock()
        return _http_client_lock

    # Recreate if the lock was created on a different loop
    if _http_client_lock is None:
        _http_client_lock = asyncio.Lock()
    else:
        try:
            # If the lock's loop doesn't match, replace it
            lock_loop = getattr(_http_client_lock, "_loop", None)
            if lock_loop is not None and lock_loop is not loop:
                _http_client_lock = asyncio.Lock()
        except Exception:
            _http_client_lock = asyncio.Lock()
    return _http_client_lock


def _create_http_client() -> httpx.AsyncClient:
    """Create the shared HTTP client."""
    return httpx.AsyncClient(timeout=httpx.Timeout(30.0))


async def _get_http_client() -> httpx.AsyncClient:
    """Return the shared HTTP client, creating it on first use.

    Safe to call concurrently from many coroutines — an asyncio.Lock
    ensures only one client is ever created.
    """
    global _http_client
    # Fast path: client already exists
    if _http_client is not None:
        return _http_client

    async with _get_client_lock():
        # Re-check after acquiring the lock (another coroutine may have created it)
        if _http_client is None:
            _http_client = _create_http_client()
        return _http_client


async def close_client() -> None:
    """Shut down the shared HTTP client (call on server exit)."""
    global _http_client
    async with _get_client_lock():
        if _http_client is None:
            return

        client = _http_client
        _http_client = None
    await client.aclose()


# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # seconds
RETRY_DELAY_MAX = 10.0  # seconds cap


# ---------------------------------------------------------------------------
# Per-connection rate-limiting
# ---------------------------------------------------------------------------


class _ConnectionState:
    """Pacing state for a single API-token bucket.

    Each instance owns its own asyncio.Lock so concurrent requests sharing the
    same token are serialised, while requests on different tokens run freely.
    """

    __slots__ = ("_lock", "backoff_until", "last_request_time")

    def __init__(self) -> None:
        self.last_request_time: float = 0.0
        self.backoff_until: float = 0.0
        self._lock: asyncio.Lock = asyncio.Lock()

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock


class RateLimiter:
    """Encapsulates per-connection pacing state and the base delay.

    Disabled by default (delay=0.0).  When disabled, ``rate_limit()`` and
    ``set_backoff()`` are true no-ops — no locks acquired, no state allocated.

    Enable by setting ``EODHD_RATE_LIMIT_DELAY`` env var to a positive float
    (e.g. ``0.1`` for 100 ms) or by calling ``set_rate_limit(seconds)``.
    """

    def __init__(self, delay: float = 0.0) -> None:
        self._delay: float = max(0.0, delay)
        self._states: dict[str, _ConnectionState] = {}
        self._states_lock: asyncio.Lock = asyncio.Lock()

    # -- public helpers -----------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self._delay > 0.0

    @property
    def delay(self) -> float:
        return self._delay

    @delay.setter
    def delay(self, value: float) -> None:
        self._delay = max(0.0, value)
        logger.info("Rate limit delay set to %.3fs (enabled=%s)", self._delay, self.enabled)

    async def get_state(self, connection_key: str) -> _ConnectionState:
        """Return the ``_ConnectionState`` for *connection_key*, creating on first use."""
        state = self._states.get(connection_key)
        if state is not None:
            return state

        async with self._states_lock:
            # Double-check after acquiring the lock
            state = self._states.get(connection_key)
            if state is None:
                state = _ConnectionState()
                self._states[connection_key] = state
            return state

    async def rate_limit(self, connection_key: str) -> None:
        """Enforce per-connection pacing and any scheduled retry backoff.

        When rate limiting is disabled (delay == 0) and no backoff is pending
        for this connection, this is a true no-op — no lock, no state created.
        Backoff (from upstream 429s / retries) is always honoured regardless.
        """
        if not self.enabled:
            # Even when disabled, honour pending backoff if state exists.
            state = self._states.get(connection_key)
            if state is None or state.backoff_until <= 0.0:
                return

        state = await self.get_state(connection_key)
        async with state.lock:
            now = time.monotonic()
            ready_at = max(state.backoff_until, state.last_request_time + self._delay)
            if now < ready_at:
                await asyncio.sleep(ready_at - now)
            now = time.monotonic()
            state.last_request_time = now
            if state.backoff_until <= now:
                state.backoff_until = 0.0

    async def set_backoff(self, connection_key: str, delay: float) -> None:
        """Schedule backoff for one connection without affecting others.

        Always honoured (even when rate limiting is disabled) because backoff
        is driven by upstream 429 / retry logic, not by the pacing delay.
        """
        if delay <= 0:
            return

        state = await self.get_state(connection_key)
        async with state.lock:
            state.backoff_until = max(state.backoff_until, time.monotonic() + delay)

    def clear(self) -> None:
        """Drop all per-connection state.  Intended for tests."""
        self._states.clear()


# Module-wide singleton — disabled by default, reads env for opt-in delay.
_rate_limiter = RateLimiter(delay=EODHD_RATE_LIMIT_DELAY)

_RETRY_AFTER_DEFAULT = 60  # seconds — fallback when header is missing or unparseable


def _parse_retry_after(header_value: str | None) -> int:
    """Parse a ``Retry-After`` header per RFC 7231 §7.1.3.

    The header may be either:
    - **delay-seconds**: a non-negative integer (e.g. ``"120"``), or
    - **HTTP-date**: e.g. ``"Thu, 01 Dec 2025 16:00:00 GMT"``

    Returns the delay in seconds (minimum 0, capped at 1 hour).
    Falls back to ``_RETRY_AFTER_DEFAULT`` on missing or unparseable values.
    """
    if not header_value:
        return _RETRY_AFTER_DEFAULT

    # Try delay-seconds first (most common)
    try:
        return max(0, min(int(header_value), 3600))
    except (ValueError, TypeError):
        pass

    # Try HTTP-date (RFC 2822 / RFC 7231)
    try:
        parsed = email.utils.parsedate_to_datetime(header_value)
        delay = int(parsed.timestamp() - time.time())
        return max(0, min(delay, 3600))
    except Exception:
        pass

    return _RETRY_AFTER_DEFAULT


# Pattern to redact api_token from URLs before logging
_TOKEN_RE = re.compile(r"api_token=[^&]+")


def _redact_url(url: str) -> str:
    """Strip api_token values from a URL for safe logging."""
    return _TOKEN_RE.sub("api_token=***", url)


def _truncate_text(text: str | None, limit: int = 2000) -> str | None:
    """Trim large response bodies so error payloads stay readable."""
    if not text:
        return None
    if len(text) > limit:
        return text[:limit] + "…"
    return text


def _extract_api_error_details(response: httpx.Response) -> tuple[str | None, str | None, str | None]:
    """Extract structured error details from an API response body when possible."""
    response_text = _truncate_text(response.text)

    try:
        payload = response.json()
    except ValueError:
        return None, None, response_text

    if not isinstance(payload, dict):
        return None, None, response_text

    def _pick_str(*keys: str) -> str | None:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    error_code = _pick_str("code", "error_code", "errorCode", "type")
    detail = _pick_str("errorMessage", "message", "detail", "description", "error_description")

    if detail is None:
        error_value = payload.get("error")
        if isinstance(error_value, str) and error_value.strip():
            detail = error_value.strip()

    return error_code, detail, response_text


def _http_status_phrase(status_code: int) -> str:
    """Return a standard reason phrase when available."""
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP Error"


def _build_http_error(
    response: httpx.Response,
    *,
    base_message: str | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured, agent-readable error payload from an HTTP response."""
    status_code = response.status_code
    error_code, upstream_message, response_text = _extract_api_error_details(response)

    error = base_message or f"EODHD API request failed with {status_code} {_http_status_phrase(status_code)}."

    payload: dict[str, Any] = {
        "error": error,
        "status_code": status_code,
    }

    if error_code:
        payload["error_code"] = error_code
    if upstream_message:
        payload["upstream_message"] = upstream_message
    if response_text:
        payload["text"] = response_text
    if extra_fields:
        payload.update(extra_fields)

    return payload


def _resolve_eodhd_token_from_request() -> str | None:
    try:
        req = get_http_request()
    except RuntimeError:
        return None
    except Exception:
        logger.debug("Unexpected error resolving HTTP request context", exc_info=True)
        return None

    # 1) Authorization: Bearer <token>
    auth = req.headers.get("authorization") or req.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        if token:
            return token

    # 2) X-API-Key (optional)
    xkey = req.headers.get("x-api-key") or req.headers.get("X-API-Key")
    if xkey:
        return xkey.strip()

    # 3) Legacy query params
    apikey = req.query_params.get("apikey")
    if apikey:
        return apikey
    return req.query_params.get("api_key") or req.query_params.get("token")


def _ensure_api_token(url: str) -> str:
    """
    Inject api_token into URL query string if missing.
    Tool-provided api_token in the URL always wins.
    """
    if "api_token=" in url:
        return url

    token = _resolve_eodhd_token_from_request() or get_api_key()
    if not token:
        return url  # best-effort; caller may have other auth patterns

    return url + (f"&api_token={token}" if "?" in url else f"?api_token={token}")


def _get_connection_key(url: str) -> str:
    """Resolve the request pacing bucket from the effective api_token."""
    query = parse_qs(urlsplit(url).query)
    token = query.get("api_token", [None])[0]
    if isinstance(token, str) and token:
        return token
    return "__default__"


def _clear_connection_states() -> None:
    """Reset request pacing state. Intended for tests."""
    _rate_limiter.clear()


def _backoff(attempt: int) -> float:
    """Exponential backoff: 1 s, 2 s, 4 s … capped at RETRY_DELAY_MAX."""
    return min(RETRY_DELAY_BASE * float(2**attempt), RETRY_DELAY_MAX)


def set_rate_limit(delay: float) -> None:
    """Override the minimum delay between requests (seconds)."""
    _rate_limiter.delay = delay


async def make_request(
    url: str,
    method: str = "GET",
    json_body: dict | None = None,
    headers: dict | None = None,
    timeout: float = 30.0,
    retry_enabled: bool | None = None,
    response_mode: Literal["json", "text", "bytes"] = "json",
) -> Any:
    """
    Generic HTTP request helper for EODHD APIs.

    - Auto-injects api_token into URL if absent.
    - Supports GET (default), POST, PUT, DELETE with optional JSON payload.
    - Backoff & retry are **disabled by default**. Enable by:
        * passing retry_enabled=True to this call, OR
        * setting the env var EODHD_RETRY_ENABLED=true
    - When enabled, retries transient failures (timeouts, 5xx) up to
      MAX_RETRIES times with exponential backoff; HTTP 429 uses Retry-After.
    - ``response_mode="json"`` returns parsed JSON on success.
    - ``response_mode="text"`` returns ``response.text`` on success.
    - ``response_mode="bytes"`` returns raw ``response.content`` on success.
    - Returns {"error": "..."} on failure.
    """
    url = _ensure_api_token(url)
    connection_key = _get_connection_key(url)
    m = (method or "GET").upper()

    if m not in ("GET", "POST", "PUT", "DELETE"):
        return {"error": f"Unsupported HTTP method: {m}"}

    req_headers: dict = {}
    if headers:
        req_headers.update(headers)

    # Ensure Content-Type for JSON bodies
    if json_body is not None:
        if "content-type" not in (k.lower() for k in req_headers):
            req_headers["Content-Type"] = "application/json"

    # Resolve effective retry count: explicit param wins, else env var
    _retry_on = retry_enabled if retry_enabled is not None else EODHD_RETRY_ENABLED
    retries = MAX_RETRIES if _retry_on else 0

    client = await _get_http_client()
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            await _rate_limiter.rate_limit(connection_key)

            logger.debug("Request attempt %d/%d: %s %s", attempt + 1, retries + 1, m, _redact_url(url)[:120])

            if m == "GET":
                response = await client.get(url, headers=req_headers, timeout=timeout)
            elif m == "POST":
                response = await client.post(url, json=json_body, headers=req_headers, timeout=timeout)
            elif m == "PUT":
                response = await client.put(url, json=json_body, headers=req_headers, timeout=timeout)
            else:  # DELETE
                response = await client.delete(url, headers=req_headers, timeout=timeout)

            # Handle rate limiting from the API
            if response.status_code == 429:
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                redacted_url = _redact_url(str(response.request.url))

                if attempt >= retries:
                    logger.error("Rate limited by API after final attempt for %s %s", m, redacted_url)
                    return _build_http_error(
                        response,
                        base_message="EODHD API rate limit exceeded (429 Too Many Requests).",
                        extra_fields={
                            "retry_after": retry_after,
                            "upstream_message": f"Retry after {retry_after} seconds.",
                        },
                    )

                logger.warning(
                    "Rate limited by API for %s %s; waiting %ds (attempt %d/%d)",
                    m,
                    redacted_url,
                    retry_after,
                    attempt + 1,
                    retries + 1,
                )
                await _rate_limiter.set_backoff(connection_key, retry_after)
                continue  # does not count as a failed attempt

            response.raise_for_status()

            if response_mode == "bytes":
                return response.content

            if response_mode == "text":
                return response.text

            # Prefer JSON; if server returns non-JSON return a helpful error object
            try:
                return response.json()
            except ValueError:
                ct = response.headers.get("content-type", "")
                text = _truncate_text(response.text)
                return {
                    "error": "Response is not valid JSON.",
                    "status_code": response.status_code,
                    "content_type": ct,
                    "text": text,
                }

        except httpx.TimeoutException as e:
            last_error = e
            logger.warning("Request timed out (attempt %d/%d)", attempt + 1, retries + 1)

        except httpx.HTTPStatusError as e:
            last_error = e
            status = e.response.status_code
            error_payload = _build_http_error(e.response)
            redacted_url = _redact_url(str(e.request.url))
            error_code = error_payload.get("error_code")
            upstream_message = error_payload.get("upstream_message")

            # 4xx (except 429 which is handled above) are not retryable
            if 400 <= status < 500:
                log_parts = [f"Client error {status} for {m} {redacted_url}"]
                if error_code:
                    log_parts.append(f"code={error_code}")
                if upstream_message:
                    log_parts.append(f"detail={upstream_message}")
                logger.error(" | ".join(log_parts))
                return error_payload

            logger.warning("Server error %d (attempt %d/%d)", status, attempt + 1, retries + 1)

        except httpx.RequestError as e:
            last_error = e
            logger.warning("Network error (attempt %d/%d): %s", attempt + 1, retries + 1, e)

        except Exception as e:
            logger.error("Unexpected error: %s", e)
            return {"error": str(e)}

        # Wait before next attempt
        if attempt < retries:
            delay = _backoff(attempt)
            logger.info("Retrying in %.1fs...", delay)
            await _rate_limiter.set_backoff(connection_key, delay)

    error_msg = str(last_error) if last_error else "Unknown error after retries"
    logger.error("All %d retries exhausted: %s", retries, error_msg)
    return {"error": error_msg}
