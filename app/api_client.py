import asyncio
import logging
import re
import time

import httpx
from .config import EODHD_API_KEY, EODHD_RETRY_ENABLED

logger = logging.getLogger("eodhd-mcp.api_client")

# Shared HTTP client — reuses TCP+TLS connections across tool calls
_http_client: httpx.AsyncClient = httpx.AsyncClient(timeout=httpx.Timeout(30.0))


async def close_client() -> None:
    """Shut down the shared HTTP client (call on server exit)."""
    await _http_client.aclose()


# Rate limiting
_last_request_time: float = 0.0
_rate_limit_delay: float = 0.1  # 100 ms between requests

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0   # seconds
RETRY_DELAY_MAX = 10.0   # seconds cap

# Pattern to redact api_token from URLs before logging
_TOKEN_RE = re.compile(r"api_token=[^&]+")


def _redact_url(url: str) -> str:
    """Strip api_token values from a URL for safe logging."""
    return _TOKEN_RE.sub("api_token=***", url)


from fastmcp.server.dependencies import get_http_request


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

    token = _resolve_eodhd_token_from_request() or EODHD_API_KEY
    if not token:
        return url  # best-effort; caller may have other auth patterns

    return url + (f"&api_token={token}" if "?" in url else f"?api_token={token}")


async def _rate_limit() -> None:
    """Enforce a minimum gap between outgoing requests."""
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < _rate_limit_delay:
        await asyncio.sleep(_rate_limit_delay - elapsed)
    _last_request_time = time.monotonic()


def _backoff(attempt: int) -> float:
    """Exponential backoff: 1 s, 2 s, 4 s … capped at RETRY_DELAY_MAX."""
    return min(RETRY_DELAY_BASE * (2 ** attempt), RETRY_DELAY_MAX)


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
) -> dict | None:
    """
    Generic HTTP request helper for EODHD APIs.

    - Auto-injects api_token into URL if absent.
    - Supports GET (default), POST, PUT, DELETE with optional JSON payload.
    - Backoff & retry are **disabled by default**. Enable by:
        * passing retry_enabled=True to this call, OR
        * setting the env var EODHD_RETRY_ENABLED=true
    - When enabled, retries transient failures (timeouts, 5xx) up to
      MAX_RETRIES times with exponential backoff; HTTP 429 uses Retry-After.
    - Returns parsed JSON dict on success, or {"error": "..."} on failure.
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

    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            await _rate_limit()

            logger.debug("Request attempt %d/%d: %s %s", attempt + 1, retries + 1, m, _redact_url(url)[:120])

            if m == "GET":
                response = await _http_client.get(url, headers=req_headers, timeout=timeout)
            elif m == "POST":
                response = await _http_client.post(url, json=json_body, headers=req_headers, timeout=timeout)
            elif m == "PUT":
                response = await _http_client.put(url, json=json_body, headers=req_headers, timeout=timeout)
            else:  # DELETE
                response = await _http_client.delete(url, headers=req_headers, timeout=timeout)

            # Handle rate limiting from the API
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning("Rate limited by API; waiting %ds (attempt %d/%d)",
                               retry_after, attempt + 1, retries + 1)
                await asyncio.sleep(retry_after)
                continue  # doesn't count as a failed attempt

            response.raise_for_status()

            # Prefer JSON; if server returns non-JSON return a helpful error object
            try:
                return response.json()
            except ValueError:
                ct = response.headers.get("content-type", "")
                text = response.text
                if text and len(text) > 2000:
                    text = text[:2000] + "…"
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

            # 4xx (except 429 which is handled above) are not retryable
            if 400 <= status < 500:
                logger.error("Client error %d: %s", status, e)
                text = e.response.text
                if text and len(text) > 2000:
                    text = text[:2000] + "…"
                return {"error": str(e), "status_code": status, "text": text}

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
