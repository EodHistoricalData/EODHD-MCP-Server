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
from fastmcp.server.dependencies import get_http_request
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

# A failure carrying no upstream status ended inside this server, and that is the whole of
# what a usage panel can say about it. Whether it arrived as a ToolError or as an
# unexpected exception is a question for the stack trace; reported as two outcomes it drew
# two bars that mean the same thing and invited the reader to tell them apart.
_LOCAL_FAILURE = "tool_error"


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
                outcome = _LOCAL_FAILURE

            self._record(kind, name, context, outcome, started_at, status_code)

            raise
        except Exception:
            self._record(kind, name, context, _LOCAL_FAILURE, started_at, None)

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

    The client identifies itself in the MCP initialize handshake. Where that handshake
    is remembered it is the better source — it is the client naming itself to MCP. It is
    not always remembered: see `_client_from_user_agent`.
    """
    fastmcp_context = getattr(context, "fastmcp_context", None)

    session_hash = None
    if fastmcp_context is not None:
        session_id = getattr(fastmcp_context, "session_id", None)
        if session_id:
            session_hash = telemetry.hash_identifier(str(session_id))

        client_info = None
        try:
            client_info = fastmcp_context.session.client_params.clientInfo
        except Exception:
            logger.debug("Client info unavailable for this session", exc_info=True)

        if client_info is not None:
            name = getattr(client_info, "name", None)
            if name:
                return name, getattr(client_info, "version", None), session_hash

    client_name, client_version = _client_from_user_agent()

    return client_name, client_version, session_hash


def _client_from_user_agent() -> tuple[str | None, str | None]:
    """The caller's name as the HTTP transport saw it, when the handshake is gone.

    Production runs with `FASTMCP_STATELESS_HTTP=1`: every request is answered on a
    fresh session, so `initialize` is never replayed and `clientInfo` is empty on every
    single call — which is why the first 1280 recorded events carried no client at all.

    The User-Agent is the only thing left that names the caller. It is a weaker signal,
    and deliberately a fallback rather than a replacement: it is not part of MCP, a
    client may send nothing or something generic (`python-httpx`), and it describes the
    HTTP library as often as the product. The handshake, where present, still wins.
    """
    try:
        request = get_http_request()
    except RuntimeError:
        # No HTTP request in scope — stdio, or a direct in-process client.
        return None, None
    except Exception:
        logger.debug("Unexpected error resolving the HTTP request context", exc_info=True)

        return None, None

    agent = (request.headers.get("user-agent") or "").strip()
    if not agent:
        return None, None

    # "Cursor/1.4.2 (darwin)" -> ("Cursor", "1.4.2"). Only the leading product token is
    # read; the comment and any further products say more about the stack than the client.
    # What comes back is a transport-level hint, not an identity: a header is whatever the
    # caller cared to send, and it names the HTTP library as readily as the product.
    name, _, version = agent.split()[0].partition("/")

    # A version with nothing to attach it to says less than nothing on a dashboard.
    if not name:
        return None, None

    return name, version or None


def install(mcp: Any, edition: str | None = None) -> None:
    """Attach the middleware to a FastMCP instance.

    Pass ``edition`` where one process hosts several — see TelemetryMiddleware.
    """
    mcp.add_middleware(TelemetryMiddleware(edition))
