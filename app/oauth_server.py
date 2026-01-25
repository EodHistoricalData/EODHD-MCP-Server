# app/oauth_server.py
"""
OAuth-enabled HTTP server wrapper for EODHD MCP Server.

Provides:
- /.well-known/oauth-protected-resource endpoint (RFC9728)
- OAuth Bearer token validation middleware
- Backward compatibility with legacy api_token
"""

import os
import json
import logging
from typing import Callable, Any

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, Mount

from .oauth import (
    get_protected_resource_metadata,
    get_www_authenticate_header,
    SCOPES,
    MCP_SERVER_URL,
    OAUTH_ISSUER,
)
from .auth import get_auth_middleware, AuthResult

logger = logging.getLogger("eodhd-mcp.oauth_server")


async def protected_resource_metadata(request: Request) -> JSONResponse:
    """
    OAuth 2.0 Protected Resource Metadata endpoint (RFC9728).

    Returns metadata about the MCP server including:
    - Authorization server location
    - Supported scopes
    - Bearer token methods
    """
    server_url = os.getenv("MCP_SERVER_URL", MCP_SERVER_URL)
    metadata = get_protected_resource_metadata(server_url)
    return JSONResponse(metadata)


async def scopes_info(request: Request) -> JSONResponse:
    """
    Return information about available scopes.
    """
    return JSONResponse({
        "scopes": SCOPES,
        "authorization_server": OAUTH_ISSUER,
    })


async def health_check(request: Request) -> JSONResponse:
    """
    Health check endpoint with auth info.
    """
    return JSONResponse({
        "status": "healthy",
        "oauth_enabled": True,
        "authorization_server": OAUTH_ISSUER,
    })


class OAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for OAuth authentication.

    Handles:
    - Bearer token extraction and validation
    - Legacy api_token fallback
    - 401 response with proper WWW-Authenticate header
    """

    def __init__(self, app, exclude_paths: list[str] = None):
        """
        Initialize OAuth middleware.

        Args:
            app: Starlette application
            exclude_paths: Paths to exclude from authentication
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/.well-known/",
            "/health",
            "/oauth/scopes",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with OAuth authentication."""
        path = request.url.path

        # Skip authentication for excluded paths
        for excluded in self.exclude_paths:
            if path.startswith(excluded):
                return await call_next(request)

        # Get authentication credentials
        auth_header = request.headers.get("Authorization")
        api_token = request.query_params.get("api_token")

        # Authenticate
        middleware = get_auth_middleware()
        auth_result = await middleware.authenticate(
            authorization_header=auth_header,
            api_token_param=api_token,
            transport="http",
        )

        if not auth_result.authenticated:
            return JSONResponse(
                status_code=401,
                content={
                    "error": auth_result.error or "unauthorized",
                    "error_description": auth_result.error_description or "Authentication required",
                },
                headers={
                    "WWW-Authenticate": get_www_authenticate_header(
                        error=auth_result.error,
                        error_description=auth_result.error_description,
                    ),
                },
            )

        # Store auth result in request state for downstream use
        request.state.auth = auth_result

        return await call_next(request)


def create_oauth_routes() -> list[Route]:
    """
    Create OAuth-related routes.

    Returns:
        List of Starlette routes
    """
    return [
        # RFC9728: Protected Resource Metadata
        Route(
            "/.well-known/oauth-protected-resource",
            protected_resource_metadata,
            methods=["GET"],
        ),
        Route(
            "/.well-known/oauth-protected-resource/{path:path}",
            protected_resource_metadata,
            methods=["GET"],
        ),

        # Additional OAuth info endpoints
        Route("/oauth/scopes", scopes_info, methods=["GET"]),
        Route("/health", health_check, methods=["GET"]),
    ]


def create_app_with_oauth(mcp_mount: Any = None) -> Starlette:
    """
    Create a Starlette app with OAuth support.

    Args:
        mcp_mount: Optional MCP application to mount

    Returns:
        Starlette application with OAuth middleware
    """
    routes = create_oauth_routes()

    # If MCP app is provided, mount it
    if mcp_mount:
        routes.append(Mount("/mcp", app=mcp_mount))

    middleware = [
        Middleware(OAuthMiddleware),
    ]

    app = Starlette(
        routes=routes,
        middleware=middleware,
        on_startup=[],
        on_shutdown=[],
    )

    return app


# Standalone server for testing
if __name__ == "__main__":
    import uvicorn

    app = create_app_with_oauth()

    uvicorn.run(
        app,
        host=os.getenv("MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("MCP_PORT", "8000")),
    )
