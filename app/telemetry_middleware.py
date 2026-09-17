# app/telemetry_middleware.py
"""One place that sees every tool call, prompt render and resource read.

FastMCP middleware wraps the dispatch, so nothing has to be added to the 75 tools
individually and nothing can be forgotten when a new one is written.

Every hook here is wrapped so that telemetry cannot change what the caller gets: the
result is returned or the exception re-raised exactly as it arrived, and any failure of
the recording itself is swallowed.
"""

import logging
import time
from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

from . import telemetry
from .api_client import resolve_account_hash

logger = logging.getLogger("eodhd-mcp.telemetry")

# EODHD raises 402 from its daily-quota limiters and nowhere else, so the status is the
# reliable signal; the wording is only a fallback for an error that carries no status at
# all. Keeping a spent quota apart from ordinary tool errors is the difference between
# "this user needs a bigger plan" and "this tool is broken".
_QUOTA_STATUS = 402
_QUOTA_MARKER = "daily API-call quota"


class TelemetryMiddleware(Middleware):
    """Records what was called, by whom, how long it took and how it ended.

    ``edition`` labels the events this instance produces ("v1" / "v2"). It is passed in
    rather than read from the environment because a single process can host more than
    one edition: in production one container serves both /v1/mcp and /v2/mcp, and an
    env var cannot tell them apart. Left unset, the environment still decides, which
    keeps the single-server and stdio cases working unchanged.
    """

    def __init__(self, edition: str | None = None) -> None:
        self.edition = edition

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
            status_code = _status_of(error)

            if status_code == _QUOTA_STATUS:
                outcome = "quota_exhausted"
            elif status_code is not None:
                outcome = "api_error"
            elif _QUOTA_MARKER in message:
                outcome = "quota_exhausted"
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
                server=self.edition,
            )
        except Exception:
            # Telemetry is never worth breaking a call that already succeeded.
            logger.debug("Recording a telemetry event failed", exc_info=True)


def _status_of(error: ToolError) -> int | None:
    """The upstream status the error carries, if it carries one.

    Read from the exception rather than from its text: `raise_on_api_error` attaches it
    where it is known, and the message now also carries the upstream reply, which is not
    ours to trust. Still bounded to real HTTP codes — the field is typed, but it comes
    from a JSON body over the wire.
    """
    status = getattr(error, "status_code", None)

    if not isinstance(status, int) or isinstance(status, bool):
        return None

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


def install(mcp: Any, edition: str | None = None) -> None:
    """Attach the middleware to a FastMCP instance.

    Pass ``edition`` where one process hosts several — see TelemetryMiddleware.
    """
    mcp.add_middleware(TelemetryMiddleware(edition))
