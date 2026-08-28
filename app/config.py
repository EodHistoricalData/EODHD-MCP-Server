# app/config.py
import os
import re

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

# Server version — keep in sync with pyproject.toml and manifest.json.
# tests/auto/test_quota_upsell.py fails the build if the three drift apart.
SERVER_VERSION = "2.3.2"


# Characters allowed in the edition label. The value reaches an HTTP header, so a
# stray newline in the deployment env would otherwise break every outbound request.
_EDITION_ALLOWED_RE = re.compile(r"[^A-Za-z0-9._-]")
_EDITION_MAX_LEN = 32


def get_user_agent() -> str:
    """User-Agent sent on every EODHD API request.

    Identifies MCP traffic in EODHD's own request logs, which otherwise sees the
    default httpx UA and cannot tell MCP apart from any other Python client.

    ``EODHD_MCP_EDITION`` (e.g. "v1" / "v2") is optional and set per deployment so
    the two servers can be told apart; read at call time, like ``get_api_key()``,
    because the env may be set after import, and sanitized because it is deployment
    input that ends up in a request header.
    """
    edition = _EDITION_ALLOWED_RE.sub("", os.environ.get("EODHD_MCP_EDITION", "").strip())[:_EDITION_MAX_LEN]
    base = f"EODHD-MCP-Server/{SERVER_VERSION}"

    return f"{base} ({edition})" if edition else base
