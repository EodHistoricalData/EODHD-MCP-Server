# app/quota.py
"""Daily-quota awareness — the state of the account's quota, cheaply and in time.

EODHD counts every call against a daily limit and answers 402 once it is spent. By then
the user's work has already stopped, so this module watches the quota while requests are
still succeeding and raises a notice while there is still room to act.

Reading the quota costs no quota: ``GET /api/user`` is not itself counted against the
daily limit (measured against production). It is not free of traffic though — it is a
request like any other, counted against the separate per-minute throttle and paced in
the same queue as the caller's own work — so a reading is taken only every
``CHECK_EVERY_N_CALLS`` calls, reusing a cached value for ``SNAPSHOT_TTL_SECONDS``.

That interval is wider than the free tier's whole daily allowance of 20 calls, so free
accounts get no notice here by design: they are not candidates for a top-up anyway, and
the message returned at the limit itself tells them what to do.

Notices are worded as statements, never as instructions to the agent — an agent that
quotes one verbatim then still reads as a sensible message to the person on the other
end.
"""

import hashlib
import logging
import time
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qs, urlsplit

logger = logging.getLogger("eodhd-mcp.quota")

# How long a reading stays fresh, and how many calls pass between readings. Together
# they bound the overhead at one extra request per minute per account, or one per 25
# calls, whichever is rarer.
SNAPSHOT_TTL_SECONDS = 60.0
CHECK_EVERY_N_CALLS = 25

# Fractions of the daily limit worth saying out loud, highest first. Each is mentioned
# at most once per account per UTC day, so a long session is not nagged.
WARNING_THRESHOLDS = (0.95, 0.80)

# One process serves many accounts and runs for weeks, so tracked accounts are capped
# and the least recently seen are dropped. None of this is worth a memory leak.
MAX_TRACKED_ACCOUNTS = 512

CONTROL_PANEL_URL = "https://eodhd.com/cp/dashboard"

# The notice travels in a ContextVar, not a module global: one process serves many API
# keys concurrently, and a global would let one account's usage surface in another
# account's response. Each MCP request runs in its own task, with its own context.
_pending_note: ContextVar[str | None] = ContextVar("eodhd_quota_note", default=None)


@dataclass(frozen=True)
class QuotaSnapshot:
    """What the account had left at the moment it was read."""

    used: int
    limit: int
    extra: int

    @property
    def fraction_used(self) -> float:
        if self.limit <= 0:
            return 0.0

        return self.used / self.limit

    @property
    def remaining(self) -> int:
        return max(self.limit - self.used, 0)

    @property
    def resets_at(self) -> datetime:
        """Next 00:00 UTC — EODHD's app timezone is UTC and the counter turns over there."""
        now = datetime.now(timezone.utc)

        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


@dataclass
class _AccountState:
    """Per-account bookkeeping.

    Every read-modify-write below happens between awaits, so the single event loop
    serialises them and no lock is needed.
    """

    snapshot: QuotaSnapshot | None = None
    fetched_at: float = 0.0
    # None until a reading has actually been attempted. A sentinel of 0.0 would be
    # read as "attempted at monotonic zero", which is *recent* on a machine whose
    # clock starts at boot — that suppressed the very first reading for the first
    # minute of uptime.
    attempted_at: float | None = None
    calls_since_check: int = 0
    announced: set[float] = field(default_factory=set)
    announced_on: str = ""
    last_seen: float = 0.0


_accounts: dict[str, _AccountState] = {}


def _cache_key(url: str) -> str | None:
    """Identify the account without keeping its token around.

    The token is read from the query because ``_ensure_api_token`` has already put it
    there by the time a request is made — in both servers, whatever the auth source
    (URL, OAuth state, Bearer, X-API-Key). Without a token there is no account to
    track, and filing such requests under a shared key would mix unrelated users.
    """
    token = parse_qs(urlsplit(url).query).get("api_token", [""])[0]
    if not token:
        return None

    return account_hash(token)


def account_hash(token: str) -> str:
    """The account's identity for bookkeeping: derived from the token, never the token."""
    return hashlib.sha256(token.encode()).hexdigest()[:16]


def _state_for(key: str) -> _AccountState:
    state = _accounts.get(key)
    if state is None:
        state = _AccountState()
        _accounts[key] = state

    state.last_seen = time.monotonic()
    _prune()

    return state


def _prune() -> None:
    while len(_accounts) > MAX_TRACKED_ACCOUNTS:
        del _accounts[min(_accounts, key=lambda key: _accounts[key].last_seen)]


def _is_account_endpoint(url: str) -> bool:
    return urlsplit(url).path.rstrip("/") == "/api/user"


def snapshot_from_payload(payload: Any) -> QuotaSnapshot | None:
    """Read the quota fields out of an /api/user response, if they are there."""
    if not isinstance(payload, dict):
        return None

    try:
        limit = int(payload["dailyRateLimit"])
        used = int(payload["apiRequests"])
    except (KeyError, TypeError, ValueError):
        return None

    try:
        extra = int(payload.get("extraLimit") or 0)
    except (TypeError, ValueError):
        extra = 0

    return QuotaSnapshot(used=used, limit=limit, extra=extra)


def describe(snapshot: QuotaSnapshot) -> dict[str, Any]:
    """Quota state in the shape a tool can hand back alongside the raw account payload."""
    return {
        "used": snapshot.used,
        "limit": snapshot.limit,
        "remaining": snapshot.remaining,
        "extraCallsInReserve": snapshot.extra,
        "percentUsed": round(snapshot.fraction_used * 100, 1),
        "resetsAt": snapshot.resets_at.isoformat().replace("+00:00", "Z"),
        "status": _status(snapshot),
    }


def _status(snapshot: QuotaSnapshot) -> str:
    if snapshot.remaining == 0 and snapshot.extra == 0:
        return "exhausted"
    if snapshot.fraction_used >= WARNING_THRESHOLDS[0]:
        return "critical"
    if snapshot.fraction_used >= WARNING_THRESHOLDS[-1]:
        return "near_limit"

    return "ok"


def format_notice(snapshot: QuotaSnapshot) -> str:
    """The sentence a user hears while there is still time to do something about it."""
    reserve = (
        f"{snapshot.extra:,} extra API calls are in reserve and are spent automatically once the daily limit is reached"
        if snapshot.extra
        else "no extra API calls are in reserve"
    )

    return (
        f"Quota notice: {snapshot.used:,} of {snapshot.limit:,} daily API calls for this key are "
        f"used ({snapshot.fraction_used * 100:.0f}%), and {reserve}. The daily counter resets at "
        f"{snapshot.resets_at.strftime('%Y-%m-%d %H:%M')} UTC. Extra API calls can be topped up, "
        "and on a paid plan the daily limit itself can be raised, in the Daily usage panel of "
        f"{CONTROL_PANEL_URL}."
    )


def _due_for_check(state: _AccountState, now: float) -> bool:
    """True once every CHECK_EVERY_N_CALLS calls for this account."""
    state.calls_since_check += 1
    if state.calls_since_check < CHECK_EVERY_N_CALLS:
        return False

    state.calls_since_check = 0

    # A previous attempt learned nothing. Waiting out the TTL keeps an outage at one
    # attempt a minute instead of one every interval; a first attempt is never delayed.
    if state.snapshot is None and state.attempted_at is not None and now - state.attempted_at < SNAPSHOT_TTL_SECONDS:
        return False

    return True


def _crossed_threshold(state: _AccountState, snapshot: QuotaSnapshot) -> float | None:
    """The highest unannounced threshold this reading has passed, if any."""
    today = datetime.now(timezone.utc).date().isoformat()
    if state.announced_on != today:
        state.announced.clear()
        state.announced_on = today

    for threshold in WARNING_THRESHOLDS:
        if snapshot.fraction_used >= threshold and threshold not in state.announced:
            # Announcing 95% settles 80% too: hearing about 80% afterwards would read
            # as though the situation had improved.
            state.announced.update(lower for lower in WARNING_THRESHOLDS if lower <= threshold)

            return threshold

    return None


def remember(url: str, payload: Any) -> None:
    """Cache a reading the caller already has, so it need not be fetched again."""
    key = _cache_key(url)
    if key is None:
        return

    snapshot = snapshot_from_payload(payload)
    if snapshot is None:
        return

    state = _state_for(key)
    state.snapshot = snapshot
    state.fetched_at = time.monotonic()


async def observe(url: str, fetch: Callable[[str], Awaitable[Any]]) -> None:
    """Read the quota behind ``url`` and leave a notice when it is running out.

    ``fetch`` is injected rather than imported so this module stays free of the HTTP
    client that calls it. Account requests are skipped: reading the quota must not
    trigger another reading of the quota.
    """
    if _is_account_endpoint(url):
        return

    key = _cache_key(url)
    if key is None:
        return

    now = time.monotonic()
    state = _state_for(key)
    if not _due_for_check(state, now):
        return

    if state.snapshot is None or now - state.fetched_at >= SNAPSHOT_TTL_SECONDS:
        state.attempted_at = now
        snapshot = await _fetch_snapshot(url, fetch)
        if snapshot is None:
            return

        state.snapshot = snapshot
        state.fetched_at = time.monotonic()

    threshold = _crossed_threshold(state, state.snapshot)
    if threshold is None:
        return

    logger.info(
        "Account passed %.0f%% of its daily quota (%d/%d used, %d extra in reserve)",
        threshold * 100,
        state.snapshot.used,
        state.snapshot.limit,
        state.snapshot.extra,
    )
    _pending_note.set(format_notice(state.snapshot))


async def _fetch_snapshot(url: str, fetch: Callable[[str], Awaitable[Any]]) -> QuotaSnapshot | None:
    split = urlsplit(url)
    account_url = f"{split.scheme}://{split.netloc}/api/user"
    token = parse_qs(split.query).get("api_token", [""])[0]
    if token:
        account_url += f"?api_token={token}&fmt=json"

    try:
        payload = await fetch(account_url)
    except Exception:
        logger.debug("Quota reading failed", exc_info=True)

        return None

    return snapshot_from_payload(payload)


def take_pending_note() -> str | None:
    """Hand over the notice for this request, if one was raised, and clear it."""
    note = _pending_note.get()
    if note is None:
        return None

    _pending_note.set(None)

    return note


def reset_state() -> None:
    """Drop every tracked account and any pending notice. For tests."""
    _accounts.clear()
    _pending_note.set(None)
