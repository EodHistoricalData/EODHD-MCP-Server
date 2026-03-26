# app/config.py
import os

from dotenv import load_dotenv

load_dotenv()
EODHD_API_BASE = "https://eodhd.com/api"


def get_api_key() -> str | None:
    """Return the current API key (re-reads env so --apikey CLI override is picked up).

    Always use this function instead of caching the key at import time —
    the value may change after ``--apikey`` is processed on the CLI.
    """
    return os.environ.get("EODHD_API_KEY")


# Set EODHD_RETRY_ENABLED=true (or 1 / yes) to enable backoff & retry globally.
EODHD_RETRY_ENABLED: bool = os.environ.get("EODHD_RETRY_ENABLED", "").lower() in ("1", "true", "yes")

# Per-connection rate-limit delay in seconds.  Disabled (0.0) by default.
# Set EODHD_RATE_LIMIT_DELAY to a positive float (e.g. "0.1") to enable.
EODHD_RATE_LIMIT_DELAY: float = float(os.environ.get("EODHD_RATE_LIMIT_DELAY", "0.0"))
