# tests/test_auth.py
"""Tests for app/auth.py module."""

import pytest
from app.auth import (
    AuthResult,
    AuthMiddleware,
    create_401_response,
    create_403_response,
    get_auth_middleware,
)


class TestAuthResult:
    """Tests for AuthResult dataclass."""

    def test_default_values(self):
        result = AuthResult()
        assert result.authenticated is False
        assert result.user_id is None
        assert result.method is None
        assert result.scopes == []
        assert result.error is None

    def test_authenticated_result(self):
        result = AuthResult(
            authenticated=True,
            user_id="123",
            method="oauth",
            scopes=["read:eod", "read:news"]
        )
        assert result.authenticated is True
        assert result.user_id == "123"
        assert result.method == "oauth"
        assert "read:eod" in result.scopes


class TestAuthMiddleware:
    """Tests for AuthMiddleware class."""

    @pytest.fixture
    def middleware(self):
        return AuthMiddleware(
            allow_legacy_api_key=True,
            allow_env_api_key=True,
        )

    def test_extract_bearer_token(self, middleware):
        # Valid Bearer token
        token = middleware.extract_bearer_token("Bearer abc123")
        assert token == "abc123"

        # Case insensitive
        token = middleware.extract_bearer_token("bearer xyz789")
        assert token == "xyz789"

        # With extra spaces
        token = middleware.extract_bearer_token("Bearer   token_with_spaces  ")
        assert token == "token_with_spaces"

        # No authorization header
        token = middleware.extract_bearer_token(None)
        assert token is None

        # Basic auth (not Bearer)
        token = middleware.extract_bearer_token("Basic YWJjOjEyMw==")
        assert token is None

    def test_check_scope(self, middleware):
        # Authenticated with matching scope
        result = AuthResult(authenticated=True, scopes=["read:eod", "read:news"])
        assert middleware.check_scope(result, "get_historical_stock_prices") is True

        # Authenticated with full-access
        result = AuthResult(authenticated=True, scopes=["full-access"])
        assert middleware.check_scope(result, "any_tool") is True

        # Not authenticated
        result = AuthResult(authenticated=False)
        assert middleware.check_scope(result, "get_historical_stock_prices") is False

    @pytest.mark.asyncio
    async def test_authenticate_stdio_with_env(self, middleware, monkeypatch):
        monkeypatch.setenv("EODHD_API_KEY", "test_key")
        # Reimport to get updated env
        from app import auth
        auth.EODHD_API_KEY = "test_key"

        result = await middleware.authenticate(transport="stdio")
        assert result.authenticated is True
        assert result.method == "env"

    @pytest.mark.asyncio
    async def test_authenticate_http_no_credentials(self, middleware, monkeypatch):
        # Clear env
        monkeypatch.delenv("EODHD_API_KEY", raising=False)
        from app import auth
        auth.EODHD_API_KEY = None

        # Create new middleware without env fallback
        mw = AuthMiddleware(allow_env_api_key=False, allow_legacy_api_key=False)
        result = await mw.authenticate(transport="http")
        assert result.authenticated is False
        assert result.error == "missing_token"


class TestCreate401Response:
    """Tests for create_401_response function."""

    def test_basic_response(self):
        response = create_401_response()
        assert response["status_code"] == 401
        assert "WWW-Authenticate" in response["headers"]
        assert response["body"]["error"] == "unauthorized"

    def test_with_scope(self):
        response = create_401_response(scope="read:eod")
        header = response["headers"]["WWW-Authenticate"]
        assert "scope=" in header

    def test_with_error(self):
        response = create_401_response(
            error="invalid_token",
            error_description="Token expired"
        )
        assert response["body"]["error"] == "invalid_token"
        assert response["body"]["error_description"] == "Token expired"


class TestCreate403Response:
    """Tests for create_403_response function."""

    def test_basic_response(self):
        response = create_403_response(required_scope="read:options")
        assert response["status_code"] == 403
        assert "WWW-Authenticate" in response["headers"]
        header = response["headers"]["WWW-Authenticate"]
        assert 'error="insufficient_scope"' in header
        assert "read:options" in header

    def test_with_description(self):
        response = create_403_response(
            required_scope="read:options",
            error_description="Options data requires subscription"
        )
        assert "Options data requires subscription" in response["body"]["error_description"]


class TestGetAuthMiddleware:
    """Tests for get_auth_middleware function."""

    def test_returns_singleton(self):
        mw1 = get_auth_middleware()
        mw2 = get_auth_middleware()
        assert mw1 is mw2

    def test_returns_auth_middleware(self):
        mw = get_auth_middleware()
        assert isinstance(mw, AuthMiddleware)
