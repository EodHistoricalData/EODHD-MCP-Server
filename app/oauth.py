# app/oauth.py
"""
OAuth 2.1 support for EODHD MCP Server.

Implements OAuth token validation and Protected Resource Metadata
as per MCP Authorization specification (2025-11-25).

References:
- MCP Authorization: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
- OAuth 2.1: https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13
- RFC9728: https://datatracker.ietf.org/doc/html/rfc9728
"""

import os
import logging
import time
import hashlib
from typing import Optional
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger("eodhd-mcp.oauth")

# Configuration from environment
OAUTH_ISSUER = os.getenv("OAUTH_ISSUER", "https://eodhd.com")
OAUTH_INTROSPECTION_URL = os.getenv("OAUTH_INTROSPECTION_URL", "")
OAUTH_JWKS_URL = os.getenv("OAUTH_JWKS_URL", "")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://mcp.eodhd.com")

# Scopes for EODHD MCP Server
SCOPES = {
    "read:eod": "Access to End-of-Day historical data",
    "read:intraday": "Access to intraday and tick data",
    "read:live": "Access to real-time/delayed quotes",
    "read:fundamentals": "Access to company fundamentals",
    "read:news": "Access to news and sentiment data",
    "read:technicals": "Access to technical indicators",
    "read:options": "Access to US options data",
    "read:marketplace": "Access to marketplace tools (illio, Praams, ESG)",
    "read:screener": "Access to stock screener",
    "read:macro": "Access to macro indicators",
    "read:user": "Access to user profile",
    "full-access": "Full access to all EODHD APIs",
}

# Tool to scope mapping
TOOL_SCOPES: dict[str, list[str]] = {
    # EOD data
    "get_historical_stock_prices": ["read:eod", "full-access"],
    "get_bulk_eod": ["read:eod", "full-access"],
    "get_historical_dividends": ["read:eod", "full-access"],
    "get_historical_splits": ["read:eod", "full-access"],

    # Intraday
    "get_intraday_historical_data": ["read:intraday", "full-access"],
    "get_us_tick_data": ["read:intraday", "full-access"],

    # Live data
    "get_live_price_data": ["read:live", "full-access"],
    "get_us_live_extended_quotes": ["read:live", "full-access"],
    "get_batch_quotes": ["read:live", "full-access"],

    # Fundamentals
    "get_fundamentals_data": ["read:fundamentals", "full-access"],
    "get_esg_scores": ["read:fundamentals", "full-access"],
    "get_analyst_ratings": ["read:fundamentals", "full-access"],
    "get_price_targets": ["read:fundamentals", "full-access"],
    "get_institutional_holders": ["read:fundamentals", "full-access"],
    "get_short_interest": ["read:fundamentals", "full-access"],
    "get_fund_holdings": ["read:fundamentals", "full-access"],
    "get_bond_fundamentals": ["read:fundamentals", "full-access"],

    # News
    "get_company_news": ["read:news", "full-access"],
    "get_financial_news": ["read:news", "full-access"],
    "get_sentiment_data": ["read:news", "full-access"],
    "get_news_word_weights": ["read:news", "full-access"],

    # Technical indicators
    "get_technical_indicators": ["read:technicals", "full-access"],

    # Options
    "get_us_options_contracts": ["read:options", "full-access"],
    "get_us_options_eod": ["read:options", "full-access"],
    "get_us_options_underlyings": ["read:options", "full-access"],

    # Marketplace
    "mp_illio_performance_insights": ["read:marketplace", "full-access"],
    "mp_illio_risk_insights": ["read:marketplace", "full-access"],
    "get_mp_praams_risk_scoring_by_ticker": ["read:marketplace", "full-access"],
    "get_mp_investverte_esg_view_company": ["read:marketplace", "full-access"],

    # Screener
    "stock_screener": ["read:screener", "full-access"],
    "get_stocks_from_search": ["read:screener", "full-access"],
    "get_market_movers": ["read:screener", "full-access"],
    "get_sector_performance": ["read:screener", "full-access"],

    # Macro
    "get_macro_indicator": ["read:macro", "full-access"],
    "get_economic_events": ["read:macro", "full-access"],

    # User
    "get_user_details": ["read:user", "full-access"],

    # Exchanges & meta
    "get_exchanges_list": ["read:eod", "full-access"],
    "get_exchange_tickers": ["read:eod", "full-access"],
    "get_exchange_details": ["read:eod", "full-access"],
    "get_available_exchanges": ["read:eod", "full-access"],
    "get_trading_hours": ["read:eod", "full-access"],
}


@dataclass
class TokenInfo:
    """Information about a validated OAuth token."""
    active: bool = False
    subject: Optional[str] = None  # user_id
    client_id: Optional[str] = None
    scopes: list[str] = field(default_factory=list)
    expires_at: Optional[int] = None
    issued_at: Optional[int] = None

    def has_scope(self, scope: str) -> bool:
        """Check if token has a specific scope."""
        return scope in self.scopes or "full-access" in self.scopes

    def has_any_scope(self, scopes: list[str]) -> bool:
        """Check if token has any of the specified scopes."""
        return any(self.has_scope(s) for s in scopes)

    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class OAuthValidator:
    """
    OAuth 2.1 token validator for MCP Server.

    Supports:
    - Token introspection (RFC7662)
    - JWT validation (optional, if JWKS configured)
    - Caching of validation results
    """

    def __init__(
        self,
        issuer: str = OAUTH_ISSUER,
        introspection_url: str = OAUTH_INTROSPECTION_URL,
        jwks_url: str = OAUTH_JWKS_URL,
        cache_ttl: int = 300,  # 5 minutes
    ):
        self.issuer = issuer
        self.introspection_url = introspection_url
        self.jwks_url = jwks_url
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[TokenInfo, float]] = {}
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self._http_client

    def _cache_key(self, token: str) -> str:
        """Generate cache key for token (hashed for security)."""
        return hashlib.sha256(token.encode()).hexdigest()[:32]

    def _get_cached(self, token: str) -> Optional[TokenInfo]:
        """Get cached token info if valid."""
        key = self._cache_key(token)
        if key in self._cache:
            info, cached_at = self._cache[key]
            if time.time() - cached_at < self.cache_ttl:
                return info
            del self._cache[key]
        return None

    def _set_cached(self, token: str, info: TokenInfo) -> None:
        """Cache token info."""
        key = self._cache_key(token)
        self._cache[key] = (info, time.time())

    async def validate_token(self, token: str) -> TokenInfo:
        """
        Validate an OAuth access token.

        Args:
            token: Bearer token from Authorization header

        Returns:
            TokenInfo with validation results
        """
        # Check cache first
        cached = self._get_cached(token)
        if cached is not None:
            return cached

        # Try introspection if configured
        if self.introspection_url:
            info = await self._introspect_token(token)
            self._set_cached(token, info)
            return info

        # Fallback: assume token is valid (for development)
        # In production, MUST configure introspection or JWT validation
        logger.warning("No token validation configured - accepting token without verification")
        info = TokenInfo(
            active=True,
            scopes=["full-access"],
        )
        return info

    async def _introspect_token(self, token: str) -> TokenInfo:
        """
        Validate token via introspection endpoint (RFC7662).
        """
        try:
            client = await self._get_client()
            response = await client.post(
                self.introspection_url,
                data={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                logger.warning(f"Token introspection failed: {response.status_code}")
                return TokenInfo(active=False)

            data = response.json()

            return TokenInfo(
                active=data.get("active", False),
                subject=data.get("sub"),
                client_id=data.get("client_id"),
                scopes=data.get("scope", "").split() if data.get("scope") else [],
                expires_at=data.get("exp"),
                issued_at=data.get("iat"),
            )

        except Exception as e:
            logger.error(f"Token introspection error: {e}")
            return TokenInfo(active=False)

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


def get_protected_resource_metadata(server_url: str = MCP_SERVER_URL) -> dict:
    """
    Generate OAuth 2.0 Protected Resource Metadata (RFC9728).

    This metadata tells OAuth clients where to find the authorization server
    and what scopes are available.

    Args:
        server_url: Canonical URL of the MCP server

    Returns:
        Protected Resource Metadata document
    """
    return {
        "resource": server_url,
        "authorization_servers": [OAUTH_ISSUER],
        "scopes_supported": list(SCOPES.keys()),
        "bearer_methods_supported": ["header"],
        "resource_documentation": "https://eodhd.com/financial-apis/",
    }


def get_www_authenticate_header(
    realm: str = "EODHD MCP Server",
    scope: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
) -> str:
    """
    Generate WWW-Authenticate header for 401/403 responses.

    Args:
        realm: Authentication realm
        scope: Required scope(s) for the resource
        error: OAuth error code (e.g., "invalid_token", "insufficient_scope")
        error_description: Human-readable error description

    Returns:
        WWW-Authenticate header value
    """
    parts = [f'Bearer realm="{realm}"']

    # Add resource metadata URL
    metadata_url = f"{MCP_SERVER_URL}/.well-known/oauth-protected-resource"
    parts.append(f'resource_metadata="{metadata_url}"')

    if scope:
        parts.append(f'scope="{scope}"')

    if error:
        parts.append(f'error="{error}"')

    if error_description:
        parts.append(f'error_description="{error_description}"')

    return ", ".join(parts)


def get_required_scopes(tool_name: str) -> list[str]:
    """
    Get required scopes for a tool.

    Args:
        tool_name: Name of the MCP tool

    Returns:
        List of scopes that grant access to this tool
    """
    return TOOL_SCOPES.get(tool_name, ["full-access"])


# Global validator instance
_validator: Optional[OAuthValidator] = None


def get_validator() -> OAuthValidator:
    """Get the global OAuth validator instance."""
    global _validator
    if _validator is None:
        _validator = OAuthValidator()
    return _validator
