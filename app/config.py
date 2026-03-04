import os
from dotenv import load_dotenv

load_dotenv()
EODHD_API_BASE = "https://eodhd.com/api"
EODHD_API_KEY = os.environ.get("EODHD_API_KEY", "demo")

# Set EODHD_RETRY_ENABLED=true (or 1 / yes) to enable backoff & retry globally.
EODHD_RETRY_ENABLED: bool = os.environ.get("EODHD_RETRY_ENABLED", "").lower() in ("1", "true", "yes")