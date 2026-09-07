# tests/auto/test_telemetry.py
"""Tests for app.telemetry and its middleware — the events the server reports itself.

Covers:
  - off unless both the collector URL and key are set
  - what an event carries, and what it deliberately does not (tokens, free text)
  - argument summarising: enumerable values kept, content counted
  - the queue is bounded and drops the oldest rather than growing
  - batches are shipped with the shared secret, and a dead collector is survivable
  - the middleware records tools, prompts and resources through a real FastMCP server
  - a failing tool is recorded and its exception still reaches the caller unchanged
"""

import asyncio
import json

import httpx
import pytest
import respx
from app import telemetry
from app.config import SERVER_VERSION
from app.telemetry_middleware import TelemetryMiddleware
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from httpx import Response

COLLECTOR = "https://cerebro.eodhd.dev/api/v1/admin/mcp/events"


@pytest.fixture
def collector(monkeypatch):
    monkeypatch.setenv("EODHD_MCP_TELEMETRY_URL", COLLECTOR)
    monkeypatch.setenv("EODHD_MCP_TELEMETRY_KEY", "collector-secret")
    monkeypatch.setenv("EODHD_MCP_EDITION", "v1")
    telemetry.reset_state()
    yield
    telemetry.reset_state()


@pytest.fixture(autouse=True)
def quiet_telemetry(monkeypatch):
    monkeypatch.delenv("EODHD_MCP_TELEMETRY_URL", raising=False)
    monkeypatch.delenv("EODHD_MCP_TELEMETRY_KEY", raising=False)
    telemetry.reset_state()
    yield
    telemetry.reset_state()


def an_event(**overrides):
    event = {
        "kind": "tool",
        "name": "get_eod_data",
        "outcome": "ok",
        "duration_ms": 120,
    }
    event.update(overrides)

    return event


# ---------------------------------------------------------------------------
# the switch
# ---------------------------------------------------------------------------


class TestEnabled:
    def test_off_by_default(self):
        assert telemetry.is_enabled() is False

    def test_off_with_only_a_url(self, monkeypatch):
        monkeypatch.setenv("EODHD_MCP_TELEMETRY_URL", COLLECTOR)

        assert telemetry.is_enabled() is False

    def test_off_with_only_a_key(self, monkeypatch):
        monkeypatch.setenv("EODHD_MCP_TELEMETRY_KEY", "collector-secret")

        assert telemetry.is_enabled() is False

    @pytest.mark.usefixtures("collector")
    def test_on_with_both(self):
        assert telemetry.is_enabled() is True

    def test_recording_while_off_queues_nothing(self):
        telemetry.record(**an_event())

        assert telemetry.queued_events() == []


# ---------------------------------------------------------------------------
# the event
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("collector")
class TestEvent:
    def test_carries_what_the_dashboard_needs(self):
        telemetry.record(
            **an_event(),
            account_hash="abc123",
            session_hash="def456",
            client_name="Claude Desktop",
            client_version="0.14.2",
            args={"exchange": "US"},
        )
        [event] = telemetry.queued_events()

        assert event["kind"] == "tool"
        assert event["name"] == "get_eod_data"
        assert event["outcome"] == "ok"
        assert event["duration_ms"] == 120
        assert event["client_name"] == "Claude Desktop"
        assert event["client_version"] == "0.14.2"
        assert event["account_hash"] == "abc123"
        assert event["session_hash"] == "def456"
        assert event["server"] == "v1"
        assert event["server_version"] == SERVER_VERSION
        assert event["occurred_at"].endswith("Z")
        assert event["event_id"]

    def test_event_ids_are_unique(self):
        telemetry.record(**an_event())
        telemetry.record(**an_event())
        first, second = telemetry.queued_events()

        assert first["event_id"] != second["event_id"]

    def test_client_labels_are_bounded_and_printable(self):
        # The client names itself; nothing stops it sending junk or an essay.
        telemetry.record(**an_event(), client_name="Claude\x00 Desktop", client_version="v" * 200)
        [event] = telemetry.queued_events()

        assert event["client_name"] == "Claude Desktop"
        assert len(event["client_version"]) == telemetry.MAX_LABEL_LENGTH

    def test_hash_identifier_is_not_the_thing_itself(self):
        hashed = telemetry.hash_identifier("super-secret-token")

        assert "super-secret-token" not in hashed
        assert len(hashed) == 16
        assert hashed == telemetry.hash_identifier("super-secret-token")


# ---------------------------------------------------------------------------
# arguments
# ---------------------------------------------------------------------------


class TestSummariseArgs:
    def test_keeps_enumerable_values(self):
        summary = telemetry.summarise_args({"exchange": "US", "interval": "1h", "period": "d"})

        assert summary == {"exchange": "US", "interval": "1h", "period": "d"}

    def test_counts_content_instead_of_recording_it(self):
        summary = telemetry.summarise_args({"symbols": ["AAPL.US", "MSFT.US", "TSLA.US"]})

        assert summary == {"symbols_count": 3}

    def test_counts_comma_separated_lists(self):
        summary = telemetry.summarise_args({"tenor": "1Y,5Y,10Y"})

        assert summary == {"tenor_count": 3}

    def test_free_text_is_dropped_entirely(self):
        summary = telemetry.summarise_args({"query": "Apple Inc", "api_token": "secret", "symbol": "AAPL.US"})

        assert summary == {}

    def test_long_values_are_truncated(self):
        summary = telemetry.summarise_args({"exchange": "X" * 100})

        assert len(summary["exchange"]) == telemetry.MAX_ARG_LENGTH

    def test_non_dict_is_harmless(self):
        assert telemetry.summarise_args(None) == {}
        assert telemetry.summarise_args("not a dict") == {}


# ---------------------------------------------------------------------------
# the queue
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("collector")
class TestQueue:
    def test_is_bounded_and_keeps_the_newest(self):
        for i in range(telemetry.MAX_QUEUED_EVENTS + 25):
            telemetry.record(**an_event(name=f"tool_{i}"))

        queued = telemetry.queued_events()

        assert len(queued) == telemetry.MAX_QUEUED_EVENTS
        assert queued[-1]["name"] == f"tool_{telemetry.MAX_QUEUED_EVENTS + 24}"
        assert telemetry.dropped_events() == 25


# ---------------------------------------------------------------------------
# shipping
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("collector")
class TestShipping:
    @pytest.mark.asyncio
    @respx.mock
    async def test_batch_goes_out_with_the_secret(self):
        route = respx.post(COLLECTOR).mock(return_value=Response(202))
        telemetry.record(**an_event())

        shipped = await telemetry.flush()

        assert shipped == 1
        request = route.calls[0].request
        assert request.headers["X-Admin-Api-Secret"] == "collector-secret"
        assert request.headers["User-Agent"].startswith("EODHD-MCP-Server/")
        # Without this the collector answers a rejected batch with a 302 to HTML
        # rather than a 422 that says which field was wrong.
        assert request.headers["Accept"] == "application/json"
        assert [event["name"] for event in json.loads(request.content)["events"]] == ["get_eod_data"]
        assert telemetry.queued_events() == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_batch_is_capped(self):
        route = respx.post(COLLECTOR).mock(return_value=Response(202))
        for _ in range(telemetry.BATCH_SIZE + 40):
            telemetry.record(**an_event())

        shipped = await telemetry.flush()

        assert shipped == telemetry.BATCH_SIZE
        assert len(telemetry.queued_events()) == 40
        assert len(route.calls) == 1

    @pytest.mark.asyncio
    @respx.mock
    async def test_an_unreachable_collector_keeps_the_batch(self):
        # Unreachable is transient by nature, so the events wait for the next attempt.
        respx.post(COLLECTOR).mock(side_effect=httpx.ConnectError("collector down"))
        telemetry.record(**an_event())

        shipped = await telemetry.flush()

        assert shipped == 0
        assert [event["name"] for event in telemetry.queued_events()] == ["get_eod_data"]

    @pytest.mark.asyncio
    @respx.mock
    async def test_a_requeued_batch_goes_out_when_the_collector_returns(self):
        route = respx.post(COLLECTOR).mock(side_effect=[httpx.ConnectError("down"), Response(202)])
        telemetry.record(**an_event())

        await telemetry.flush()
        shipped = await telemetry.flush()

        assert shipped == 1
        assert len(route.calls) == 2
        assert telemetry.queued_events() == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_a_rejected_batch_is_dropped(self):
        # A refusal is about the batch or the key; retrying it forever helps nobody.
        respx.post(COLLECTOR).mock(return_value=Response(403))
        telemetry.record(**an_event())

        assert await telemetry.flush() == 0
        assert telemetry.queued_events() == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_an_outage_is_announced_once_and_recovery_too(self, caplog):
        respx.post(COLLECTOR).mock(side_effect=[httpx.ConnectError("down"), httpx.ConnectError("down"), Response(202)])
        telemetry.record(**an_event())

        with caplog.at_level("WARNING", logger="eodhd-mcp.telemetry"):
            await telemetry.flush()
            await telemetry.flush()
            warnings_while_failing = [r for r in caplog.records if r.levelname == "WARNING"]
            await telemetry.flush()

        assert len(warnings_while_failing) == 1  # not once per failed attempt
        assert "reachable again" in caplog.text

    @pytest.mark.asyncio
    @respx.mock
    async def test_a_full_batch_ships_without_waiting_for_the_interval(self):
        route = respx.post(COLLECTOR).mock(return_value=Response(202))

        for _ in range(telemetry.BATCH_SIZE):
            telemetry.record(**an_event())
        await asyncio.sleep(0)  # let the scheduled flush run
        await asyncio.sleep(0)

        assert len(route.calls) == 1

    @pytest.mark.asyncio
    async def test_flush_while_off_is_a_no_op(self):
        assert await telemetry.flush() == 0

    @pytest.mark.asyncio
    async def test_shutdown_without_a_worker_is_safe(self):
        await telemetry.shutdown()


# ---------------------------------------------------------------------------
# the middleware, against a real server
# ---------------------------------------------------------------------------


def server_with_telemetry() -> FastMCP:
    mcp = FastMCP("telemetry-test")
    mcp.add_middleware(TelemetryMiddleware())

    @mcp.tool
    def get_eod_data(exchange: str = "US") -> str:
        """A tool that succeeds."""
        return "ok"

    @mcp.tool
    def broken_tool() -> str:
        """A tool that fails."""
        raise ToolError("EODHD API request failed with 403 Forbidden. | status_code=403")

    @mcp.tool
    def out_of_quota() -> str:
        """A tool that hits the daily limit."""
        raise ToolError("status_code=402 | The daily API-call quota for this EODHD API key is used up.")

    @mcp.resource("eodhd://docs/{page}")
    def docs(page: str) -> str:
        """A resource that never touches the API."""
        return f"documentation for {page}"

    @mcp.prompt
    def analyze_stock(ticker: str) -> str:
        """A prompt template."""
        return f"Analyse {ticker}"

    return mcp


@pytest.mark.usefixtures("collector")
class TestMiddleware:
    @pytest.mark.asyncio
    async def test_records_a_successful_tool_call(self):
        async with Client(server_with_telemetry()) as client:
            await client.call_tool("get_eod_data", {"exchange": "LSE"})

        [event] = telemetry.queued_events()

        assert event["kind"] == "tool"
        assert event["name"] == "get_eod_data"
        assert event["outcome"] == "ok"
        assert event["args"] == {"exchange": "LSE"}
        assert event["duration_ms"] >= 0
        assert event["client_name"]  # the FastMCP test client identifies itself
        assert event["session_hash"]

    @pytest.mark.asyncio
    async def test_records_a_failure_and_still_raises_it(self):
        with pytest.raises(ToolError, match="403"):
            async with Client(server_with_telemetry()) as client:
                await client.call_tool("broken_tool", {})

        [event] = telemetry.queued_events()

        assert event["outcome"] == "api_error"
        assert event["status_code"] == 403

    @pytest.mark.asyncio
    async def test_a_spent_quota_is_its_own_outcome(self):
        with pytest.raises(ToolError, match="daily API-call quota"):
            async with Client(server_with_telemetry()) as client:
                await client.call_tool("out_of_quota", {})

        [event] = telemetry.queued_events()

        assert event["outcome"] == "quota_exhausted"
        assert event["status_code"] == 402

    @pytest.mark.asyncio
    async def test_records_a_prompt(self):
        async with Client(server_with_telemetry()) as client:
            await client.get_prompt("analyze_stock", {"ticker": "AAPL.US"})

        [event] = telemetry.queued_events()

        assert event["kind"] == "prompt"
        assert event["name"] == "analyze_stock"
        assert event["args"] == {}  # the ticker is content, and content is not recorded

    @pytest.mark.asyncio
    async def test_records_a_resource_read(self):
        # The point of the whole exercise: this never reaches EODHD, so nothing but the
        # server itself can report it.
        async with Client(server_with_telemetry()) as client:
            await client.read_resource("eodhd://docs/fundamentals")

        [event] = telemetry.queued_events()

        assert event["kind"] == "resource"
        assert event["name"] == "eodhd://docs/fundamentals"
        assert event["outcome"] == "ok"


class TestMiddlewareWithoutCollector:
    """The class above runs with the collector fixture; this one deliberately does not."""

    @pytest.mark.asyncio
    async def test_records_nothing_while_telemetry_is_off(self):
        async with Client(server_with_telemetry()) as client:
            result = await client.call_tool("get_eod_data", {"exchange": "US"})

        assert result is not None  # the call still works
        assert telemetry.queued_events() == []
