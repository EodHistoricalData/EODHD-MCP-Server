import os

from dotenv import load_dotenv

load_dotenv()
EODHD_API_BASE = "https://eodhd.com/api"
EODHD_API_KEY = os.environ.get("EODHD_API_KEY")


def get_api_key() -> str | None:
    """Return the current API key (re-reads env so --apikey CLI override is picked up)."""
    return os.environ.get("EODHD_API_KEY")


# Set EODHD_RETRY_ENABLED=true (or 1 / yes) to enable backoff & retry globally.
EODHD_RETRY_ENABLED: bool = os.environ.get("EODHD_RETRY_ENABLED", "").lower() in ("1", "true", "yes")
