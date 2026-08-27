# tests/auto/test_quota_awareness.py
"""Tests for app.quota — noticing the daily limit before it is hit.

Covers:
  - snapshot arithmetic: remaining, percentage, reset time, status
  - the notice text: real numbers, statements only
  - readings are taken every CHECK_EVERY_N_CALLS calls, not per request
  - a reading is cached, and an account response refreshes the cache for free
  - each threshold is announced once per account per day
  - the notice is per-request state, never shared between concurrent accounts
  - account requests never trigger a reading of themselves
"""

import asyncio
import json
from datetime import datetime, timezone

import pytest
import respx
from app import quota
from app.api_client import make_request
from app.quota import QuotaSnapshot
from app.response_formatter import format_json_response
from app.tools.get_user_details import register as register_user_details
from fastmcp import FastMCP
from httpx import Response


@pytest.fixture(autouse=True)
def clean_quota_state():
    quota.reset_state()
    yield
    quota.reset_state()


def account_payload(used: int, limit: int = 100_000, extra: int = 0) -> dict:
    return {
        "name": "Test User",
        "apiRequests": used,
        "apiRequestsDate": "2026-08-26",
        "dailyRateLimit": limit,
        "extraLimit": extra,
    }


async def fetch_returning(payload, calls: list[str]):
    async def fetch(url: str):
        calls.append(url)

        return payload

    return fetch


# ---------------------------------------------------------------------------
# snapshot arithmetic
# ---------------------------------------------------------------------------


class TestSnapshot:
    def test_remaining_and_fraction(self):
        snapshot = QuotaSnapshot(used=82_000, limit=100_000, extra=0)

        assert snapshot.remaining == 18_000
        assert snapshot.fraction_used == pytest.approx(0.82)

    def test_remaining_never_goes_negative(self):
        # Extra calls keep serving requests after the daily limit is passed.
        snapshot = QuotaSnapshot(used=120_000, limit=100_000, extra=50_000)

        assert snapshot.remaining == 0

    def test_unlimited_account_is_not_a_division_by_zero(self):
        assert QuotaSnapshot(used=10, limit=0, extra=0).fraction_used == 0.0

    def test_resets_at_next_utc_midnight(self):
        resets_at = QuotaSnapshot(used=1, limit=10, extra=0).resets_at
        now = datetime.now(timezone.utc)

        assert (resets_at.hour, resets_at.minute, resets_at.second) == (0, 0, 0)
        assert resets_at > now
        assert (resets_at - now).total_seconds() <= 24 * 3600

    @pytest.mark.parametrize(
        ("used", "extra", "status"),
        [
            (10_000, 0, "ok"),
            (80_000, 0, "near_limit"),
            (96_000, 0, "critical"),
            (100_000, 0, "exhausted"),
            (100_000, 50_000, "critical"),  # a reserve means work can still continue
        ],
    )
    def test_status(self, used, extra, status):
        assert quota.describe(QuotaSnapshot(used=used, limit=100_000, extra=extra))["status"] == status

    def test_describe_shape(self):
        described = quota.describe(QuotaSnapshot(used=82_000, limit=100_000, extra=1_000))

        assert described["used"] == 82_000
        assert described["remaining"] == 18_000
        assert described["extraCallsInReserve"] == 1_000
        assert described["percentUsed"] == 82.0
        assert described["resetsAt"].endswith("Z")

    def test_malformed_payload_yields_no_snapshot(self):
        assert quota.snapshot_from_payload({"name": "no quota fields"}) is None
        assert quota.snapshot_from_payload("not a dict") is None
        assert quota.snapshot_from_payload({"apiRequests": "x", "dailyRateLimit": "y"}) is None


# ---------------------------------------------------------------------------
# the notice
# ---------------------------------------------------------------------------


class TestNotice:
    def test_carries_the_real_numbers(self):
        notice = quota.format_notice(QuotaSnapshot(used=82_000, limit=100_000, extra=0))

        assert "82,000 of 100,000" in notice
        assert "82%" in notice
        assert "no extra API calls are in reserve" in notice
        assert quota.CONTROL_PANEL_URL in notice

    def test_mentions_a_reserve_when_there_is_one(self):
        notice = quota.format_notice(QuotaSnapshot(used=96_000, limit=100_000, extra=250_000))

        assert "250,000 extra API calls are in reserve" in notice

    def test_is_written_as_statements(self):
        notice = quota.format_notice(QuotaSnapshot(used=82_000, limit=100_000, extra=0))

        for imperative in ("Tell the user", "Relay ", "Give the user", "you should", "please "):
            assert imperative not in notice


# ---------------------------------------------------------------------------
# when a reading is taken
# ---------------------------------------------------------------------------


class TestObserve:
    @pytest.mark.asyncio
    async def test_no_reading_before_the_interval(self):
        calls: list[str] = []
        fetch = await fetch_returning(account_payload(90_000), calls)

        for _ in range(quota.CHECK_EVERY_N_CALLS - 1):
            await quota.observe("https://eodhd.com/api/eod/AAPL.US?api_token=t", fetch)

        assert calls == []
        assert quota.take_pending_note() is None

    @pytest.mark.asyncio
    async def test_reading_on_the_interval_raises_a_notice(self):
        calls: list[str] = []
        fetch = await fetch_returning(account_payload(90_000), calls)

        for _ in range(quota.CHECK_EVERY_N_CALLS):
            await quota.observe("https://eodhd.com/api/eod/AAPL.US?api_token=t", fetch)

        assert len(calls) == 1
        assert calls[0].startswith("https://eodhd.com/api/user")
        assert "90,000 of 100,000" in (quota.take_pending_note() or "")

    @pytest.mark.asyncio
    async def test_quiet_while_there_is_room(self):
        calls: list[str] = []
        fetch = await fetch_returning(account_payload(1_000), calls)

        for _ in range(quota.CHECK_EVERY_N_CALLS * 2):
            await quota.observe("https://eodhd.com/api/eod/AAPL.US?api_token=t", fetch)

        assert quota.take_pending_note() is None

    @pytest.mark.asyncio
    async def test_each_threshold_is_announced_once(self):
        url = "https://eodhd.com/api/eod/AAPL.US?api_token=t"
        calls: list[str] = []
        fetch = await fetch_returning(account_payload(82_000), calls)

        async def run_interval():
            for _ in range(quota.CHECK_EVERY_N_CALLS):
                await quota.observe(url, fetch)

        await run_interval()
        assert quota.take_pending_note() is not None  # 80% announced

        quota.remember(url, account_payload(82_000))  # fresh reading, same usage
        await run_interval()
        assert quota.take_pending_note() is None  # not announced twice

        quota.remember(url, account_payload(96_000))
        await run_interval()
        assert quota.take_pending_note() is not None  # 95% is its own threshold

    @pytest.mark.asyncio
    async def test_passing_the_higher_threshold_settles_the_lower_one(self):
        # Announcing 95% and then 80% would read as though the situation had improved.
        url = "https://eodhd.com/api/eod/AAPL.US?api_token=t"
        calls: list[str] = []
        fetch = await fetch_returning(account_payload(96_000), calls)

        for _ in range(quota.CHECK_EVERY_N_CALLS):
            await quota.observe(url, fetch)
        assert "96%" in (quota.take_pending_note() or "")

        quota.remember(url, account_payload(97_000))
        for _ in range(quota.CHECK_EVERY_N_CALLS):
            await quota.observe(url, fetch)

        assert quota.take_pending_note() is None

    @pytest.mark.asyncio
    async def test_untracked_when_the_url_carries_no_token(self):
        # Filing keyless requests under a shared bucket would mix unrelated users.
        calls: list[str] = []
        fetch = await fetch_returning(account_payload(96_000), calls)

        for _ in range(quota.CHECK_EVERY_N_CALLS * 2):
            await quota.observe("https://eodhd.com/api/eod/AAPL.US", fetch)

        assert calls == []
        assert quota.take_pending_note() is None

    @pytest.mark.asyncio
    async def test_tracked_accounts_are_capped(self):
        calls: list[str] = []
        fetch = await fetch_returning(account_payload(10), calls)

        for i in range(quota.MAX_TRACKED_ACCOUNTS + 50):
            await quota.observe(f"https://eodhd.com/api/eod/AAPL.US?api_token=key-{i}", fetch)

        assert len(quota._accounts) == quota.MAX_TRACKED_ACCOUNTS

    @pytest.mark.asyncio
    async def test_first_reading_is_not_suppressed_on_a_freshly_booted_machine(self, monkeypatch):
        # time.monotonic() counts from boot on Linux, so on a machine up for less than
        # the TTL the "wait out a failed attempt" guard used to swallow the first
        # reading — it read the never-attempted sentinel as a recent attempt. CI's
        # cold runners caught this; a long-running laptop never would.
        monkeypatch.setattr(quota.time, "monotonic", lambda: 4.0)
        calls: list[str] = []
        fetch = await fetch_returning(account_payload(96_000), calls)

        for _ in range(quota.CHECK_EVERY_N_CALLS):
            await quota.observe("https://eodhd.com/api/eod/AAPL.US?api_token=t", fetch)

        assert len(calls) == 1
        assert "96%" in (quota.take_pending_note() or "")

    @pytest.mark.asyncio
    async def test_a_failed_reading_is_not_retried_every_interval(self):
        attempts: list[str] = []

        async def failing(url: str):
            attempts.append(url)
            raise RuntimeError("network down")

        for _ in range(quota.CHECK_EVERY_N_CALLS * 3):
            await quota.observe("https://eodhd.com/api/eod/AAPL.US?api_token=t", failing)

        assert len(attempts) == 1  # three intervals, one attempt — the backoff held

    @pytest.mark.asyncio
    async def test_reading_is_cached_across_intervals(self):
        calls: list[str] = []
        fetch = await fetch_returning(account_payload(10_000), calls)

        for _ in range(quota.CHECK_EVERY_N_CALLS * 3):
            await quota.observe("https://eodhd.com/api/eod/AAPL.US?api_token=t", fetch)

        assert len(calls) == 1  # three intervals, one request — the TTL held

    @pytest.mark.asyncio
    async def test_account_response_refreshes_the_cache_for_free(self):
        calls: list[str] = []
        fetch = await fetch_returning(account_payload(99_000), calls)
        url = "https://eodhd.com/api/eod/AAPL.US?api_token=t"

        quota.remember(url, account_payload(99_000))
        for _ in range(quota.CHECK_EVERY_N_CALLS):
            await quota.observe(url, fetch)

        assert calls == []  # nothing fetched: the account payload was already at hand
        assert "99,000" in (quota.take_pending_note() or "")

    @pytest.mark.asyncio
    async def test_account_requests_do_not_read_themselves(self):
        calls: list[str] = []
        fetch = await fetch_returning(account_payload(90_000), calls)

        for _ in range(quota.CHECK_EVERY_N_CALLS * 2):
            await quota.observe("https://eodhd.com/api/user?api_token=t", fetch)

        assert calls == []

    @pytest.mark.asyncio
    async def test_a_failed_reading_is_not_fatal(self):
        async def fetch(url: str):
            raise RuntimeError("network down")

        for _ in range(quota.CHECK_EVERY_N_CALLS):
            await quota.observe("https://eodhd.com/api/eod/AAPL.US?api_token=t", fetch)

        assert quota.take_pending_note() is None

    @pytest.mark.asyncio
    async def test_accounts_are_counted_separately(self):
        calls: list[str] = []
        fetch = await fetch_returning(account_payload(90_000), calls)

        for _ in range(quota.CHECK_EVERY_N_CALLS - 1):
            await quota.observe("https://eodhd.com/api/eod/AAPL.US?api_token=token-a", fetch)
        await quota.observe("https://eodhd.com/api/eod/AAPL.US?api_token=token-b", fetch)

        assert calls == []  # token-b is one call in, token-a is one short


# ---------------------------------------------------------------------------
# isolation between concurrent accounts
# ---------------------------------------------------------------------------


class TestNoticeIsolation:
    @pytest.mark.asyncio
    async def test_notice_does_not_leak_into_another_account_request(self):
        calls: list[str] = []
        loud = await fetch_returning(account_payload(96_000), calls)
        quiet = await fetch_returning(account_payload(10, limit=1_000_000), calls)
        seen: dict[str, str | None] = {}

        async def session(name: str, token: str, fetch):
            for _ in range(quota.CHECK_EVERY_N_CALLS):
                await quota.observe(f"https://eodhd.com/api/eod/AAPL.US?api_token={token}", fetch)
            seen[name] = quota.take_pending_note()

        await asyncio.gather(
            session("loud", "token-loud", loud),
            session("quiet", "token-quiet", quiet),
        )

        assert seen["loud"] is not None
        assert seen["quiet"] is None  # the busy account's usage stayed in its own request

    @pytest.mark.asyncio
    async def test_note_is_handed_over_once(self):
        calls: list[str] = []
        fetch = await fetch_returning(account_payload(96_000), calls)

        for _ in range(quota.CHECK_EVERY_N_CALLS):
            await quota.observe("https://eodhd.com/api/eod/AAPL.US?api_token=t", fetch)

        assert quota.take_pending_note() is not None
        assert quota.take_pending_note() is None


# ---------------------------------------------------------------------------
# end to end: the notice reaches the agent, the account tool carries the numbers
# ---------------------------------------------------------------------------


class TestReachesTheAgent:
    @pytest.mark.asyncio
    @respx.mock
    async def test_notice_rides_along_with_the_next_response(self):
        respx.get(url__startswith="https://eodhd.com/api/user").mock(
            return_value=Response(200, json=account_payload(96_000))
        )
        respx.get(url__startswith="https://eodhd.com/api/eod/AAPL.US").mock(
            return_value=Response(200, json=[{"close": 150.0}])
        )

        for _ in range(quota.CHECK_EVERY_N_CALLS):
            data = await make_request("https://eodhd.com/api/eod/AAPL.US?api_token=t")

        response = format_json_response(data)

        assert len(response) == 2  # the data, plus the notice as its own resource
        assert response[1].resource.mimeType == "text/plain"
        assert "96,000 of 100,000" in response[1].resource.text

    @pytest.mark.asyncio
    @respx.mock
    async def test_a_calm_account_gets_the_data_alone(self):
        respx.get(url__startswith="https://eodhd.com/api/user").mock(
            return_value=Response(200, json=account_payload(100))
        )
        respx.get(url__startswith="https://eodhd.com/api/eod/AAPL.US").mock(
            return_value=Response(200, json=[{"close": 150.0}])
        )

        for _ in range(quota.CHECK_EVERY_N_CALLS):
            data = await make_request("https://eodhd.com/api/eod/AAPL.US?api_token=t")

        assert len(format_json_response(data)) == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_account_tool_reports_what_is_left(self):
        respx.get(url__startswith="https://eodhd.com/api/user").mock(
            return_value=Response(200, json=account_payload(82_000, extra=5_000))
        )

        server = FastMCP("test")
        register_user_details(server)
        tool = await server.get_tool("get_user_details")
        result = await tool.run({"api_token": "t"})

        payload = json.loads(result.content[0].resource.text)

        assert payload["quota"]["remaining"] == 18_000
        assert payload["quota"]["percentUsed"] == 82.0
        assert payload["quota"]["status"] == "near_limit"
        assert payload["quota"]["extraCallsInReserve"] == 5_000
        assert payload["apiRequests"] == 82_000  # the raw fields are still there
