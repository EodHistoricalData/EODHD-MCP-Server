# app/telemetry.py
"""Usage telemetry — what happens inside this server, reported by the server itself.

EODHD's request logs see HTTP calls and nothing else. They cannot see which client is
on the other end, the tools that never touch the API (embedded docs, computed levels),
a prompt that fans out into five calls, or a failure that is not an HTTP failure. Those
facts exist only here, so this is where they are collected.

Nothing here may cost the caller anything. Events are queued, shipped in batches by a
background task, dropped when the queue is full, and every failure is swallowed — a
collector that is down or slow must never delay, fail or alter a tool call. The emitter
stays off unless both ``EODHD_MCP_TELEMETRY_URL`` and ``EODHD_MCP_TELEMETRY_KEY`` are
set, so a deployment without a collector emits nothing at all.

What is deliberately not collected: tokens (an account is a hash), emails, and free-text
arguments. Only enumerable argument values are kept — see ``REPORTED_ARGS``.
"""

import asyncio
import contextlib
import hashlib
import logging
import os
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any

import httpx

from .config import SERVER_VERSION, get_edition, get_user_agent

logger = logging.getLogger("eodhd-mcp.telemetry")

# A batch leaves when either threshold is reached, whichever comes first.
BATCH_SIZE = 200
FLUSH_INTERVAL_SECONDS = 30.0

# The queue is a ring: when a collector is down, the newest events matter more than a
# backlog nobody will read, and unbounded growth is not an option in a long-lived server.
MAX_QUEUED_EVENTS = 2_000

REQUEST_TIMEOUT_SECONDS = 5.0

# Argument names worth keeping. Every one of them is a short enumerable value — an
# exchange, a market, an interval. Symbols, queries and anything else free-text are
# counted, never recorded: they are user content, and this is a usage metric.
REPORTED_ARGS = frozenset({"exchange", "market", "interval", "period", "order", "fmt", "asset_type", "type"})
MAX_ARG_LENGTH = 24

# Every mutation below happens between awaits on one event loop, so the module state
# needs no lock; the only concurrency is the shipping task, which yields only inside the
# HTTP call.
_queue: deque[dict[str, Any]] = deque(maxlen=MAX_QUEUED_EVENTS)
_dropped = 0
_consecutive_failures = 0
_worker: asyncio.Task | None = None
_flush_task: asyncio.Task | None = None
_client: httpx.AsyncClient | None = None


def get_collector_url() -> str | None:
    """Read at call time, like the API key: the env may be set after import."""
    return os.environ.get("EODHD_MCP_TELEMETRY_URL", "").strip() or None


def get_collector_key() -> str | None:
    return os.environ.get("EODHD_MCP_TELEMETRY_KEY", "").strip() or None


def is_enabled() -> bool:
    """Both halves are required: a URL without a key would post to a collector that
    rejects it, and a key without a URL has nowhere to go."""
    return get_collector_url() is not None and get_collector_key() is not None


def hash_identifier(value: str) -> str:
    """Identify an account or a session without keeping the thing itself."""
    return hashlib.sha256(value.encode()).hexdigest()[:16]


MAX_LABEL_LENGTH = 64


def clean_label(value: Any) -> str | None:
    """Bound a self-reported client name or version — it is untrusted input."""
    if not isinstance(value, str):
        return None

    cleaned = "".join(char for char in value if char.isprintable()).strip()[:MAX_LABEL_LENGTH]

    return cleaned or None


def summarise_args(arguments: Any) -> dict[str, Any]:
    """Keep the enumerable arguments, count the rest, record nothing that is content."""
    if not isinstance(arguments, dict):
        return {}

    summary: dict[str, Any] = {}
    for name, value in arguments.items():
        if name in REPORTED_ARGS and isinstance(value, str | int | float | bool):
            summary[name] = str(value)[:MAX_ARG_LENGTH]
        elif isinstance(value, (list, tuple)):
            summary[f"{name}_count"] = len(value)
        elif isinstance(value, str) and "," in value:
            # Comma-separated lists are how several tools take multiple symbols.
            summary[f"{name}_count"] = len([part for part in value.split(",") if part.strip()])

    return summary


def record(
    *,
    kind: str,
    name: str,
    outcome: str,
    duration_ms: int,
    account_hash: str | None = None,
    session_hash: str | None = None,
    client_name: str | None = None,
    client_version: str | None = None,
    status_code: int | None = None,
    args: dict[str, Any] | None = None,
) -> None:
    """Queue one event. Cheap, synchronous, and silent when telemetry is off."""
    if not is_enabled():
        return

    global _dropped
    if len(_queue) == _queue.maxlen:
        _dropped += 1

    _queue.append(
        {
            "event_id": str(uuid.uuid4()),
            "occurred_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "server": get_edition() or "unknown",
            "server_version": SERVER_VERSION,
            "client_name": clean_label(client_name),
            "client_version": clean_label(client_version),
            "session_hash": session_hash,
            "account_hash": account_hash,
            "kind": kind,
            "name": name,
            "outcome": outcome,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "args": args or {},
        }
    )

    _ensure_worker()

    if len(_queue) >= BATCH_SIZE:
        _schedule_flush()


def _schedule_flush() -> None:
    """Send a full batch now rather than let it wait out the interval."""
    global _flush_task
    if _flush_task is not None and not _flush_task.done():
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    _flush_task = loop.create_task(flush())


def _ensure_worker() -> None:
    """Start the shipping task on the running loop, once."""
    global _worker
    if _worker is not None and not _worker.done():
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return  # no loop yet; the next recorded event starts the worker

    _worker = loop.create_task(_ship_forever())


async def _ship_forever() -> None:
    while True:
        try:
            await asyncio.sleep(FLUSH_INTERVAL_SECONDS)
            await flush()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.debug("Telemetry worker iteration failed", exc_info=True)


async def flush() -> int:
    """Ship what is queued. Returns how many events left; never raises."""
    if not _queue or not is_enabled():
        return 0

    global _consecutive_failures, _dropped

    batch = [_queue.popleft() for _ in range(min(BATCH_SIZE, len(_queue)))]
    try:
        await _post(batch)
    except httpx.HTTPStatusError as error:
        # The collector understood and refused: a bad key, a bad payload, a route that
        # is not there. Retrying cannot fix any of those, so the batch goes.
        _note_failure(f"collector rejected a batch of {len(batch)} with {error.response.status_code}")

        return 0
    except Exception:
        # Unreachable, timed out, TLS trouble — transient by nature, so the batch goes
        # back to the front for the next flush to try again.
        #
        # Only as much of it as still fits, though. `extendleft` on a full ring evicts
        # from the RIGHT, and the right is where record() appends — so a blind requeue
        # discards the freshest events to make room for the stalest, and does it
        # silently, because _dropped only ever grew in record(). With an unreachable
        # collector and a live stream of calls that is exactly the case that happens.
        # The oldest of the batch are the ones to lose, and the loss gets counted.
        room = max((_queue.maxlen or len(batch)) - len(_queue), 0)
        if room < len(batch):
            _dropped += len(batch) - room
            batch = batch[len(batch) - room :]

        if batch:
            _queue.extendleft(reversed(batch))

        _note_failure(f"collector unreachable, {len(batch)} events requeued")

        return 0

    if _consecutive_failures:
        logger.warning("Telemetry collector reachable again after %d failed attempts", _consecutive_failures)
        _consecutive_failures = 0

    return len(batch)


def _note_failure(what: str) -> None:
    """Say it out loud the first time, then keep quiet — a broken collector should be
    discoverable without filling the log for as long as it stays broken."""
    global _consecutive_failures
    _consecutive_failures += 1

    if _consecutive_failures == 1:
        logger.warning("Telemetry: %s", what, exc_info=True)
    else:
        logger.debug("Telemetry: %s (failure %d in a row)", what, _consecutive_failures, exc_info=True)


async def _post(batch: list[dict[str, Any]]) -> None:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS),
            # Accept is not decoration: the collector is a Laravel app, and without it a
            # rejected batch comes back as a 302 to an HTML page instead of a 422 naming
            # the field that was wrong. We drop the batch either way — but one of those
            # two is readable in a log and the other is not.
            #
            # The User-Agent is set per request instead, for the same reason as in
            # api_client: this client outlives any change to EODHD_MCP_EDITION.
            headers={"Accept": "application/json"},
        )

    url = get_collector_url()
    key = get_collector_key()
    if url is None or key is None:
        return

    response = await _client.post(
        url,
        json={"events": batch},
        headers={"X-Admin-Api-Secret": key, "User-Agent": get_user_agent()},
    )
    response.raise_for_status()


def dropped_events() -> int:
    """Events evicted by a full queue since start — the honest size of the blind spot."""
    return _dropped


async def shutdown() -> None:
    """Stop the worker and let a last batch out. Safe to call when never started."""
    global _worker, _flush_task, _client

    for task in (_worker, _flush_task):
        if task is None:
            continue

        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    _worker = None
    _flush_task = None

    with contextlib.suppress(Exception):
        await flush()

    if _client is not None:
        with contextlib.suppress(Exception):
            await _client.aclose()
        _client = None


def reset_state() -> None:
    """Drop the queue, the counters and the task handles. For tests.

    Unlike `shutdown()` this is synchronous and so cannot await `aclose()`. Dropping the
    reference alone left a connection pool behind on every call — harmless in production,
    where nothing calls this, but it is a leak per test that touches telemetry. Closed on
    the running loop when there is one; when there is not, there is no client to close
    either, since one can only have been created from inside a coroutine.
    """
    global _worker, _flush_task, _dropped, _consecutive_failures, _client
    _queue.clear()
    _dropped = 0
    _consecutive_failures = 0
    _worker = None
    _flush_task = None

    client, _client = _client, None
    if client is not None:
        try:
            asyncio.get_running_loop().create_task(client.aclose())
        except RuntimeError:
            pass


def queued_events() -> list[dict[str, Any]]:
    """A copy of what is waiting to be shipped. For tests and diagnostics."""
    return list(_queue)


def monotonic_ms(started_at: float) -> int:
    return max(int((time.perf_counter() - started_at) * 1000), 0)
