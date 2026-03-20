import os

from dotenv import load_dotenv

load_dotenv()
EODHD_API_BASE = "https://eodhd.com/api"


def get_api_key() -> str:
    """Return the current EODHD API key (reads env at call time, not import time)."""
    return os.environ.get("EODHD_API_KEY", "demo")


# Set EODHD_RETRY_ENABLED=true (or 1 / yes) to enable backoff & retry globally.
EODHD_RETRY_ENABLED: bool = os.environ.get("EODHD_RETRY_ENABLED", "").lower() in ("1", "true", "yes")
