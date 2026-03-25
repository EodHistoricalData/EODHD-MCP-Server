# app/api_client.py
import asyncio
import logging
import re
import time
from http import HTTPStatus
from typing import Any, Literal

import httpx
from fastmcp.server.dependencies import get_http_request

from .config import EODHD_RETRY_ENABLED, get_api_key

logger = logging.getLogger("eodhd-mcp.api_client")

# Shared HTTP client — created lazily inside a running event loop
_http_client: httpx.AsyncClient | None = None


def _create_http_client() -> httpx.AsyncClient:
    """Create the shared HTTP client."""
    return httpx.AsyncClient(timeout=httpx.Timeout(30.0))


async def _get_http_client() -> httpx.AsyncClient:
    """Return the shared HTTP client, creating it on first use."""
    global _http_client
    if _http_client is None:
        _http_client = _create_http_client()
    return _http_client


async def close_client() -> None:
    """Shut down the shared HTTP client (call on server exit)."""
    global _http_client
    if _http_client is None:
        return

    client = _http_client
    _http_client = None
    await client.aclose()


# Rate limiting
_last_request_time: float = 0.0
_rate_limit_delay: float = 0.1  # 100 ms between requests
_rate_limit_lock: asyncio.Lock | None = None
_rate_limit_lock_loop: asyncio.AbstractEventLoop | None = None


def _get_rate_limit_lock() -> asyncio.Lock:
    """Return the rate-limit lock for the current event loop."""
    global _rate_limit_lock, _rate_limit_lock_loop
    loop = asyncio.get_running_loop()
    if _rate_limit_lock is None or _rate_limit_lock_loop is not loop:
        _rate_limit_lock = asyncio.Lock()
        _rate_limit_lock_loop = loop
    return _rate_limit_lock


# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # seconds
RETRY_DELAY_MAX = 10.0  # seconds cap

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


async def _rate_limit() -> None:
    """Enforce a minimum gap between outgoing requests."""
    global _last_request_time
    async with _get_rate_limit_lock():
        now = time.monotonic()
        elapsed = now - _last_request_time
        if elapsed < _rate_limit_delay:
            await asyncio.sleep(_rate_limit_delay - elapsed)
        _last_request_time = time.monotonic()


def _backoff(attempt: int) -> float:
    """Exponential backoff: 1 s, 2 s, 4 s … capped at RETRY_DELAY_MAX."""
    return min(RETRY_DELAY_BASE * float(2**attempt), RETRY_DELAY_MAX)


def set_rate_limit(delay: float) -> None:
    """Override the minimum delay between requests (seconds)."""
    global _rate_limit_delay
    _rate_limit_delay = max(0.0, delay)
    logger.info("Rate limit delay set to %.3fs", _rate_limit_delay)


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
            await _rate_limit()

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
                retry_after = int(response.headers.get("Retry-After", 60))
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
                await asyncio.sleep(retry_after)
                continue  # doesn't count as a failed attempt

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
            logger.info("Retrying in %.1fs…", delay)
            await asyncio.sleep(delay)

    error_msg = str(last_error) if last_error else "Unknown error after retries"
    logger.error("All %d retries exhausted: %s", retries, error_msg)
    return {"error": error_msg}
