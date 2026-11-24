"""MCP protocol settings shared by every FastMCP instance this project builds.

MCP revision 2026-07-28 changed what a server advertises about itself:

- `ttlMs` / `cacheScope` ride every `*/list`, `resources/read` and `server/discover`
  result. The SDK fills them from the hint passed to the `FastMCP` constructor.
  Every list and every reference resource is the same for all callers (static
  tool catalogue, static markdown files), so the hint is `public`. If a list or a
  resource ever starts depending on the caller, the scope must become `private`.
- the `logging` capability is deprecated. The SDK declares it whenever a
  `logging/setLevel` handler exists, and FastMCP always registers one. The server
  never sends log notifications, so the capability is dropped from both the
  `initialize` and the `server/discover` result. The handler itself stays, so an
  older client that still calls `logging/setLevel` gets a normal answer.
"""

from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext

from .config import SERVER_VERSION

CACHE_TTL_SECONDS = 300
CACHE_SCOPE = "public"


def server_options() -> dict[str, Any]:
    """Keyword arguments for every `FastMCP(...)` constructor in the project."""
    return {
        "version": SERVER_VERSION,
        "cache_ttl": CACHE_TTL_SECONDS,
        "cache_scope": CACHE_SCOPE,
    }


class DeprecatedCapabilitiesMiddleware(Middleware):
    """Remove capabilities that MCP 2026-07-28 deprecated from what the server advertises."""

    async def on_initialize(self, context: MiddlewareContext, call_next: Any) -> Any:
        return _without_logging(await call_next(context))

    async def on_discover(self, context: MiddlewareContext, call_next: Any) -> Any:
        return _without_logging(await call_next(context))


def install(mcp: Any) -> None:
    """Attach the protocol middleware to a FastMCP instance."""
    mcp.add_middleware(DeprecatedCapabilitiesMiddleware())


def _without_logging(result: Any) -> Any:
    capabilities = getattr(result, "capabilities", None)
    if capabilities is not None:
        capabilities.logging = None

    return result
