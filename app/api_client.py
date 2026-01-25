# app/api_client.py
"""
HTTP client for EODHD API with retry logic and rate limiting.
"""

import asyncio
import logging
import time
from typing import Any, Optional

import httpx

from .config import EODHD_API_KEY

logger = logging.getLogger("eodhd-mcp.api_client")

# Rate limiting configuration
_last_request_time: float = 0
_rate_limit_delay: float = 0.1  # 100ms between requests

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # Base delay in seconds
RETRY_DELAY_MAX = 10.0  # Maximum delay


class APIError(Exception):
    """Custom exception for API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


async def _rate_limit() -> None:
    """Apply rate limiting between requests."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < _rate_limit_delay:
        await asyncio.sleep(_rate_limit_delay - elapsed)
    _last_request_time = time.time()


def _calculate_retry_delay(attempt: int) -> float:
    """Calculate delay for retry with exponential backoff."""
    delay = RETRY_DELAY_BASE * (2 ** attempt)
    return min(delay, RETRY_DELAY_MAX)


async def make_request(
    url: str,
    timeout: float = 30.0,
    retries: int = MAX_RETRIES
) -> dict | list | None:
    """
    Make an HTTP GET request to the EODHD API with retry logic and rate limiting.

    Args:
        url: The API endpoint URL
        timeout: Request timeout in seconds
        retries: Number of retry attempts

    Returns:
        JSON response as dict/list or error dict
    """
    # Add API token if not present
    if "api_token=" not in url:
        separator = "&" if "?" in url else "?"
        url += f"{separator}api_token={EODHD_API_KEY}"

    last_error: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            # Apply rate limiting
            await _rate_limit()

            async with httpx.AsyncClient() as client:
                logger.debug(f"Request attempt {attempt + 1}: {url[:100]}...")
                response = await client.get(url, timeout=timeout)

                # Handle rate limiting from API
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()

                # Try to parse JSON
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    return response.json()
                elif "text/csv" in content_type or "text/plain" in content_type:
                    # Return CSV as-is wrapped in dict
                    return {"csv": response.text}
                else:
                    # Try JSON anyway
                    try:
                        return response.json()
                    except Exception:
                        return {"text": response.text}

        except httpx.TimeoutException as e:
            last_error = e
            logger.warning(f"Request timeout (attempt {attempt + 1}/{retries + 1})")

        except httpx.HTTPStatusError as e:
            last_error = e
            status = e.response.status_code

            # Don't retry client errors (4xx) except 429
            if 400 <= status < 500 and status != 429:
                logger.error(f"Client error {status}: {e}")
                return {"error": f"HTTP {status}: {str(e)}"}

            logger.warning(f"Server error {status} (attempt {attempt + 1}/{retries + 1})")

        except httpx.RequestError as e:
            last_error = e
            logger.warning(f"Request error (attempt {attempt + 1}/{retries + 1}): {e}")

        except Exception as e:
            last_error = e
            logger.error(f"Unexpected error: {e}")
            return {"error": str(e)}

        # Calculate retry delay with exponential backoff
        if attempt < retries:
            delay = _calculate_retry_delay(attempt)
            logger.info(f"Retrying in {delay:.1f}s...")
            await asyncio.sleep(delay)

    # All retries exhausted
    error_msg = str(last_error) if last_error else "Unknown error after retries"
    logger.error(f"All retries exhausted: {error_msg}")
    return {"error": error_msg}


async def make_post_request(
    url: str,
    data: Optional[dict] = None,
    json_data: Optional[dict] = None,
    timeout: float = 30.0
) -> dict | None:
    """
    Make an HTTP POST request to the EODHD API.

    Args:
        url: The API endpoint URL
        data: Form data to send
        json_data: JSON data to send
        timeout: Request timeout in seconds

    Returns:
        JSON response as dict or error dict
    """
    # Add API token if not present
    if "api_token=" not in url:
        separator = "&" if "?" in url else "?"
        url += f"{separator}api_token={EODHD_API_KEY}"

    try:
        await _rate_limit()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                data=data,
                json=json_data,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()

    except Exception as e:
        logger.error(f"POST request failed: {e}")
        return {"error": str(e)}


def set_rate_limit(delay: float) -> None:
    """Set the rate limit delay between requests."""
    global _rate_limit_delay
    _rate_limit_delay = max(0.0, delay)
    logger.info(f"Rate limit set to {_rate_limit_delay}s")
