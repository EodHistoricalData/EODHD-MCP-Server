# app/auth.py
"""
Authentication middleware for EODHD MCP Server.

Supports dual authentication:
1. OAuth 2.1 Bearer tokens (for HTTP transport per MCP spec)
2. Legacy API key (backward compatibility)

Per MCP Authorization Specification:
- STDIO transport: credentials from environment (EODHD_API_KEY)
- HTTP transport: OAuth 2.1 Bearer tokens

This module provides backward compatibility by accepting both methods.
"""

import os
import logging
import re
from typing import Optional, Callable, Any
from dataclasses import dataclass

import httpx

from .oauth import (
    OAuthValidator,
    TokenInfo,
    get_validator,
    get_www_authenticate_header,
    get_required_scopes,
    SCOPES,
)
from .config import EODHD_API_KEY

logger = logging.getLogger("eodhd-mcp.auth")

# Legacy API token validation endpoint
EODHD_USER_API = "https://eodhd.com/api/user"


@dataclass
class AuthResult:
    """Result of authentication attempt."""
    authenticated: bool = False
    user_id: Optional[str] = None
    method: Optional[str] = None  # "oauth", "api_key", "env"
    scopes: list[str] = None
    error: Optional[str] = None
    error_description: Optional[str] = None

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = []


class AuthMiddleware:
    """
    Authentication middleware supporting OAuth and legacy API keys.

    Authentication priority:
    1. OAuth Bearer token from Authorization header
    2. Legacy api_token from query/body parameter
    3. EODHD_API_KEY from environment (for STDIO transport)
    """

    def __init__(
        self,
        oauth_validator: Optional[OAuthValidator] = None,
        allow_legacy_api_key: bool = True,
        allow_env_api_key: bool = True,
    ):
        """
        Initialize auth middleware.

        Args:
            oauth_validator: OAuth token validator instance
            allow_legacy_api_key: Allow api_token parameter (backward compat)
            allow_env_api_key: Allow EODHD_API_KEY from environment
        """
        self.oauth_validator = oauth_validator or get_validator()
        self.allow_legacy_api_key = allow_legacy_api_key
        self.allow_env_api_key = allow_env_api_key
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for API key validation."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self._http_client

    def extract_bearer_token(self, authorization_header: Optional[str]) -> Optional[str]:
        """
        Extract Bearer token from Authorization header.

        Args:
            authorization_header: Value of Authorization header

        Returns:
            Token string or None
        """
        if not authorization_header:
            return None

        match = re.match(r"Bearer\s+(.+)", authorization_header, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    async def validate_legacy_api_key(self, api_key: str) -> AuthResult:
        """
        Validate legacy EODHD API key.

        Args:
            api_key: API key to validate

        Returns:
            AuthResult with validation status
        """
        try:
            client = await self._get_client()
            response = await client.get(
                EODHD_USER_API,
                params={"api_token": api_key, "fmt": "json"},
            )

            if response.status_code == 200:
                data = response.json()
                return AuthResult(
                    authenticated=True,
                    user_id=str(data.get("id", "")),
                    method="api_key",
                    scopes=["full-access"],  # Legacy API keys have full access
                )
            else:
                return AuthResult(
                    authenticated=False,
                    error="invalid_token",
                    error_description="Invalid or expired API key",
                )

        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return AuthResult(
                authenticated=False,
                error="server_error",
                error_description="Failed to validate API key",
            )

    async def authenticate(
        self,
        authorization_header: Optional[str] = None,
        api_token_param: Optional[str] = None,
        transport: str = "http",
    ) -> AuthResult:
        """
        Authenticate a request using available credentials.

        Args:
            authorization_header: Authorization header value
            api_token_param: api_token from query/body params
            transport: Transport type ("http", "sse", "stdio")

        Returns:
            AuthResult with authentication status
        """
        # For STDIO transport, use environment variable
        if transport == "stdio":
            if self.allow_env_api_key and EODHD_API_KEY:
                return AuthResult(
                    authenticated=True,
                    method="env",
                    scopes=["full-access"],
                )
            return AuthResult(
                authenticated=False,
                error="missing_token",
                error_description="EODHD_API_KEY environment variable not set",
            )

        # Try OAuth Bearer token first
        bearer_token = self.extract_bearer_token(authorization_header)
        if bearer_token:
            token_info = await self.oauth_validator.validate_token(bearer_token)
            if token_info.active and not token_info.is_expired():
                return AuthResult(
                    authenticated=True,
                    user_id=token_info.subject,
                    method="oauth",
                    scopes=token_info.scopes,
                )
            else:
                return AuthResult(
                    authenticated=False,
                    error="invalid_token",
                    error_description="Token is invalid or expired",
                )

        # Try legacy api_token parameter
        if self.allow_legacy_api_key and api_token_param:
            return await self.validate_legacy_api_key(api_token_param)

        # Try environment API key as fallback for HTTP
        if self.allow_env_api_key and EODHD_API_KEY:
            logger.debug("Using environment API key for HTTP request")
            return AuthResult(
                authenticated=True,
                method="env",
                scopes=["full-access"],
            )

        # No valid credentials found
        return AuthResult(
            authenticated=False,
            error="missing_token",
            error_description="No valid authentication credentials provided",
        )

    def check_scope(self, auth_result: AuthResult, tool_name: str) -> bool:
        """
        Check if authenticated user has required scope for a tool.

        Args:
            auth_result: Authentication result
            tool_name: Name of the tool being accessed

        Returns:
            True if user has required scope
        """
        if not auth_result.authenticated:
            return False

        required_scopes = get_required_scopes(tool_name)
        return any(scope in auth_result.scopes for scope in required_scopes)

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


def create_401_response(
    scope: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
) -> dict:
    """
    Create a 401 Unauthorized response with proper headers.

    Args:
        scope: Required scope for the resource
        error: OAuth error code
        error_description: Error description

    Returns:
        Response dict with status and headers
    """
    return {
        "status_code": 401,
        "headers": {
            "WWW-Authenticate": get_www_authenticate_header(
                scope=scope,
                error=error,
                error_description=error_description,
            ),
        },
        "body": {
            "error": error or "unauthorized",
            "error_description": error_description or "Authentication required",
        },
    }


def create_403_response(
    required_scope: str,
    error_description: Optional[str] = None,
) -> dict:
    """
    Create a 403 Forbidden response for insufficient scope.

    Args:
        required_scope: Scope(s) required for the resource
        error_description: Error description

    Returns:
        Response dict with status and headers
    """
    return {
        "status_code": 403,
        "headers": {
            "WWW-Authenticate": get_www_authenticate_header(
                scope=required_scope,
                error="insufficient_scope",
                error_description=error_description or f"Required scope: {required_scope}",
            ),
        },
        "body": {
            "error": "insufficient_scope",
            "error_description": error_description or f"Required scope: {required_scope}",
        },
    }


# Global middleware instance
_middleware: Optional[AuthMiddleware] = None


def get_auth_middleware() -> AuthMiddleware:
    """Get the global auth middleware instance."""
    global _middleware
    if _middleware is None:
        _middleware = AuthMiddleware()
    return _middleware
