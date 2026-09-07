# app/telemetry_middleware.py
"""One place that sees every tool call, prompt render and resource read.

FastMCP middleware wraps the dispatch, so nothing has to be added to the 75 tools
individually and nothing can be forgotten when a new one is written.

Every hook here is wrapped so that telemetry cannot change what the caller gets: the
result is returned or the exception re-raised exactly as it arrived, and any failure of
the recording itself is swallowed.
"""

import logging
import re
import time
from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

from . import telemetry
from .api_client import resolve_account_hash

logger = logging.getLogger("eodhd-mcp.telemetry")

_STATUS_RE = re.compile(r"status_code=(\d{3})")

# EODHD raises 402 from its daily-quota limiters and nowhere else, so the status is the
# reliable signal; the wording is only a fallback for a message that lost it. Keeping a
# spent quota apart from ordinary tool errors is the difference between "this user needs
# a bigger plan" and "this tool is broken".
_QUOTA_STATUS = 402
_QUOTA_MARKER = "daily API-call quota"


class TelemetryMiddleware(Middleware):
    """Records what was called, by whom, how long it took and how it ended."""

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        return await self._observe("tool", getattr(context.message, "name", "unknown"), context, call_next)

    async def on_get_prompt(self, context: MiddlewareContext, call_next: Any) -> Any:
        return await self._observe("prompt", getattr(context.message, "name", "unknown"), context, call_next)

    async def on_read_resource(self, context: MiddlewareContext, call_next: Any) -> Any:
        name = str(getattr(context.message, "uri", "unknown"))

        return await self._observe("resource", name, context, call_next)

    async def _observe(self, kind: str, name: str, context: MiddlewareContext, call_next: Any) -> Any:
        if not telemetry.is_enabled():
            return await call_next(context)

        started_at = time.perf_counter()
        outcome = "ok"
        status_code = None

        try:
            result = await call_next(context)
        except ToolError as error:
            message = str(error)
            status_code = _status_from(message)

            if status_code == _QUOTA_STATUS or _QUOTA_MARKER in message:
                outcome = "quota_exhausted"
            elif status_code is not None:
                outcome = "api_error"
            else:
                outcome = "tool_error"

            self._record(kind, name, context, outcome, started_at, status_code)

            raise
        except Exception:
            self._record(kind, name, context, "error", started_at, None)

            raise

        self._record(kind, name, context, outcome, started_at, status_code)

        return result

    def _record(
        self,
        kind: str,
        name: str,
        context: MiddlewareContext,
        outcome: str,
        started_at: float,
        status_code: int | None,
    ) -> None:
        try:
            client_name, client_version, session_hash = _session_facts(context)
            telemetry.record(
                kind=kind,
                name=name,
                outcome=outcome,
                duration_ms=telemetry.monotonic_ms(started_at),
                account_hash=resolve_account_hash(),
                session_hash=session_hash,
                client_name=client_name,
                client_version=client_version,
                status_code=status_code,
                args=telemetry.summarise_args(getattr(context.message, "arguments", None)),
            )
        except Exception:
            # Telemetry is never worth breaking a call that already succeeded.
            logger.debug("Recording a telemetry event failed", exc_info=True)


def _status_from(message: str) -> int | None:
    """The upstream status, when the message carries one this server put there.

    Bounded to real HTTP codes so a tool that happens to echo "status_code=999" back
    from user content cannot invent an API failure in the dashboard.
    """
    match = _STATUS_RE.search(message)
    if match is None:
        return None

    status = int(match.group(1))

    return status if 100 <= status <= 599 else None


def _session_facts(context: MiddlewareContext) -> tuple[str | None, str | None, str | None]:
    """Client name, client version and a hashed session id, as far as they are known.

    The client identifies itself once, in the MCP initialize handshake, and that is the
    only place this is ever available — no HTTP log can recover it afterwards.
    """
    fastmcp_context = getattr(context, "fastmcp_context", None)
    if fastmcp_context is None:
        return None, None, None

    session_hash = None
    session_id = getattr(fastmcp_context, "session_id", None)
    if session_id:
        session_hash = telemetry.hash_identifier(str(session_id))

    client_info = None
    try:
        client_info = fastmcp_context.session.client_params.clientInfo
    except Exception:
        logger.debug("Client info unavailable for this session", exc_info=True)

    if client_info is None:
        return None, None, session_hash

    return getattr(client_info, "name", None), getattr(client_info, "version", None), session_hash


def install(mcp: Any) -> None:
    """Attach the middleware to a FastMCP instance."""
    mcp.add_middleware(TelemetryMiddleware())
