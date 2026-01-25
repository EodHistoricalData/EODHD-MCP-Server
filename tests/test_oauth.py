# tests/test_oauth.py
"""Tests for app/oauth.py module."""

import pytest
from app.oauth import (
    TokenInfo,
    OAuthValidator,
    get_protected_resource_metadata,
    get_www_authenticate_header,
    get_required_scopes,
    SCOPES,
    TOOL_SCOPES,
)


class TestTokenInfo:
    """Tests for TokenInfo dataclass."""

    def test_default_values(self):
        info = TokenInfo()
        assert info.active is False
        assert info.subject is None
        assert info.scopes == []

    def test_has_scope(self):
        info = TokenInfo(active=True, scopes=["read:eod", "read:news"])
        assert info.has_scope("read:eod") is True
        assert info.has_scope("read:options") is False

    def test_has_scope_full_access(self):
        info = TokenInfo(active=True, scopes=["full-access"])
        assert info.has_scope("read:eod") is True
        assert info.has_scope("read:anything") is True

    def test_has_any_scope(self):
        info = TokenInfo(active=True, scopes=["read:eod"])
        assert info.has_any_scope(["read:eod", "read:news"]) is True
        assert info.has_any_scope(["read:options", "read:news"]) is False

    def test_is_expired(self):
        import time
        # Not expired
        info = TokenInfo(expires_at=int(time.time()) + 3600)
        assert info.is_expired() is False

        # Expired
        info = TokenInfo(expires_at=int(time.time()) - 100)
        assert info.is_expired() is True

        # No expiration
        info = TokenInfo(expires_at=None)
        assert info.is_expired() is False


class TestOAuthValidator:
    """Tests for OAuthValidator class."""

    def test_init(self):
        validator = OAuthValidator()
        assert validator.cache_ttl == 300
        assert validator._cache == {}

    def test_cache_key(self):
        validator = OAuthValidator()
        key1 = validator._cache_key("token1")
        key2 = validator._cache_key("token2")
        assert key1 != key2
        assert len(key1) == 32

    def test_caching(self):
        validator = OAuthValidator()
        info = TokenInfo(active=True, scopes=["read:eod"])
        validator._set_cached("test_token", info)

        cached = validator._get_cached("test_token")
        assert cached is not None
        assert cached.active is True
        assert cached.scopes == ["read:eod"]

    def test_cache_miss(self):
        validator = OAuthValidator()
        cached = validator._get_cached("nonexistent")
        assert cached is None

    @pytest.mark.asyncio
    async def test_validate_token_no_introspection(self):
        """When no introspection URL is configured, accept token with warning."""
        validator = OAuthValidator(introspection_url="")
        info = await validator.validate_token("any_token")
        # Should return valid with full-access (dev mode)
        assert info.active is True
        assert "full-access" in info.scopes


class TestProtectedResourceMetadata:
    """Tests for get_protected_resource_metadata function."""

    def test_returns_metadata(self):
        metadata = get_protected_resource_metadata("https://mcp.example.com")
        assert "resource" in metadata
        assert metadata["resource"] == "https://mcp.example.com"
        assert "authorization_servers" in metadata
        assert "scopes_supported" in metadata
        assert "bearer_methods_supported" in metadata

    def test_scopes_in_metadata(self):
        metadata = get_protected_resource_metadata()
        scopes = metadata["scopes_supported"]
        assert "read:eod" in scopes
        assert "full-access" in scopes


class TestWWWAuthenticateHeader:
    """Tests for get_www_authenticate_header function."""

    def test_basic_header(self):
        header = get_www_authenticate_header()
        assert 'Bearer realm=' in header
        assert 'resource_metadata=' in header

    def test_with_scope(self):
        header = get_www_authenticate_header(scope="read:eod")
        assert 'scope="read:eod"' in header

    def test_with_error(self):
        header = get_www_authenticate_header(
            error="invalid_token",
            error_description="Token has expired"
        )
        assert 'error="invalid_token"' in header
        assert 'error_description="Token has expired"' in header


class TestGetRequiredScopes:
    """Tests for get_required_scopes function."""

    def test_known_tool(self):
        scopes = get_required_scopes("get_historical_stock_prices")
        assert "read:eod" in scopes
        assert "full-access" in scopes

    def test_unknown_tool(self):
        scopes = get_required_scopes("unknown_tool")
        assert "full-access" in scopes

    def test_options_tool(self):
        scopes = get_required_scopes("get_us_options_contracts")
        assert "read:options" in scopes


class TestScopes:
    """Tests for scope definitions."""

    def test_scopes_defined(self):
        assert len(SCOPES) > 0
        assert "read:eod" in SCOPES
        assert "full-access" in SCOPES

    def test_tool_scopes_defined(self):
        assert len(TOOL_SCOPES) > 0
        # All tools should have full-access as an option
        for tool, scopes in TOOL_SCOPES.items():
            assert "full-access" in scopes, f"Tool {tool} missing full-access scope"
