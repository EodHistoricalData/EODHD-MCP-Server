# tests/auto/test_quota_upsell.py
"""Tests for the daily-quota (HTTP 402) path.

EODHD returns 402 from its rate limiters only, and its own request log drops 402
before writing, so this server is where a quota hit becomes visible and where the
agent is told what the user can actually do about it.

Covers:
  - get_user_agent: identifies MCP traffic, optional per-deployment edition
  - outbound requests carry that User-Agent
  - 402 increments the local quota counter; other statuses do not
  - raise_on_api_error appends the self-serve options only on 402
  - version stays in sync across config / pyproject / manifest
"""

import json
import pathlib
import re

import pytest
import respx
from app.api_client import (
    close_client,
    get_quota_exhausted_hits,
    make_request,
)
from app.config import SERVER_VERSION, get_user_agent
from app.response_formatter import (
    QUOTA_CONTROL_PANEL_URL,
    QUOTA_EXHAUSTED_HINT,
    raise_on_api_error,
)
from fastmcp.exceptions import ToolError
from httpx import Response

QUOTA_402_BODY = "API Rate Limit Exceeded. Please, contact our support team: support@eodhistoricaldata.com"

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# get_user_agent
# ---------------------------------------------------------------------------


class TestUserAgent:
    def test_identifies_the_mcp_server(self, monkeypatch):
        monkeypatch.delenv("EODHD_MCP_EDITION", raising=False)
        assert get_user_agent() == f"EODHD-MCP-Server/{SERVER_VERSION}"

    def test_edition_suffix_when_set(self, monkeypatch):
        monkeypatch.setenv("EODHD_MCP_EDITION", "v2")
        assert get_user_agent() == f"EODHD-MCP-Server/{SERVER_VERSION} (v2)"

    def test_blank_edition_is_ignored(self, monkeypatch):
        monkeypatch.setenv("EODHD_MCP_EDITION", "   ")
        assert get_user_agent() == f"EODHD-MCP-Server/{SERVER_VERSION}"

    def test_control_characters_are_stripped(self, monkeypatch):
        # A newline in the deployment env would otherwise make httpx reject the header.
        monkeypatch.setenv("EODHD_MCP_EDITION", "v2\r\nX-Injected: 1")
        agent = get_user_agent()

        assert "\n" not in agent and "\r" not in agent
        assert agent == f"EODHD-MCP-Server/{SERVER_VERSION} (v2X-Injected1)"

    def test_edition_is_length_capped(self, monkeypatch):
        monkeypatch.setenv("EODHD_MCP_EDITION", "v" * 100)
        assert get_user_agent() == f"EODHD-MCP-Server/{SERVER_VERSION} ({'v' * 32})"

    @pytest.mark.asyncio
    @respx.mock
    async def test_sanitized_edition_still_builds_a_client(self, monkeypatch):
        monkeypatch.setenv("EODHD_MCP_EDITION", "v1\nbad")
        await close_client()

        route = respx.get(url__startswith="https://eodhd.com/api/eod/AAPL.US").mock(
            return_value=Response(200, json=[{"close": 150.0}])
        )

        await make_request("https://eodhd.com/api/eod/AAPL.US")
        await close_client()

        assert route.calls[0].request.headers["User-Agent"] == f"EODHD-MCP-Server/{SERVER_VERSION} (v1bad)"

    def test_read_at_call_time(self, monkeypatch):
        monkeypatch.setenv("EODHD_MCP_EDITION", "v1")
        first = get_user_agent()
        monkeypatch.setenv("EODHD_MCP_EDITION", "v2")
        assert get_user_agent() != first

    @pytest.mark.asyncio
    @respx.mock
    async def test_sent_on_outbound_requests(self, monkeypatch):
        monkeypatch.delenv("EODHD_MCP_EDITION", raising=False)
        await close_client()  # drop any client built with a different UA

        route = respx.get(url__startswith="https://eodhd.com/api/eod/AAPL.US").mock(
            return_value=Response(200, json=[{"close": 150.0}])
        )

        await make_request("https://eodhd.com/api/eod/AAPL.US")
        await close_client()

        assert route.calls[0].request.headers["User-Agent"] == f"EODHD-MCP-Server/{SERVER_VERSION}"


# ---------------------------------------------------------------------------
# quota counter
# ---------------------------------------------------------------------------


class TestQuotaCounter:
    @pytest.mark.asyncio
    @respx.mock
    async def test_402_is_counted_and_logged(self, caplog):
        respx.get(url__startswith="https://eodhd.com/api/eod/AAPL.US").mock(
            return_value=Response(402, text=QUOTA_402_BODY)
        )

        before = get_quota_exhausted_hits()
        with caplog.at_level("WARNING", logger="eodhd-mcp.quota"):
            result = await make_request("https://eodhd.com/api/eod/AAPL.US?api_token=SECRET123")

        assert result["status_code"] == 402
        assert get_quota_exhausted_hits() == before + 1
        assert "EODHD daily quota exhausted (402)" in caplog.text
        assert "SECRET123" not in caplog.text  # the URL is redacted before logging

    @pytest.mark.asyncio
    @respx.mock
    async def test_other_client_errors_are_not_counted(self):
        respx.get(url__startswith="https://eodhd.com/api/eod/BAD").mock(
            return_value=Response(403, json={"error": "Forbidden"})
        )

        before = get_quota_exhausted_hits()
        await make_request("https://eodhd.com/api/eod/BAD")

        assert get_quota_exhausted_hits() == before


# ---------------------------------------------------------------------------
# raise_on_api_error — what the agent reads
# ---------------------------------------------------------------------------


class TestQuotaHint:
    def test_402_carries_the_self_serve_options(self):
        payload = {
            "error": "EODHD API request failed with 402 Payment Required.",
            "status_code": 402,
            "text": QUOTA_402_BODY,
        }

        with pytest.raises(ToolError) as exc:
            raise_on_api_error(payload)

        message = str(exc.value)
        assert QUOTA_EXHAUSTED_HINT in message
        assert QUOTA_CONTROL_PANEL_URL in message
        assert "extra API calls" in message
        assert "00:00 UTC" in message

    def test_402_keeps_the_upstream_message(self):
        payload = {
            "error": "EODHD API request failed with 402 Payment Required.",
            "status_code": 402,
            "text": QUOTA_402_BODY,
        }

        with pytest.raises(ToolError) as exc:
            raise_on_api_error(payload)

        assert QUOTA_402_BODY in str(exc.value)
        assert "status_code=402" in str(exc.value)

    @pytest.mark.parametrize("status_code", [400, 401, 403, 404, 422, 429, 500])
    def test_other_statuses_get_no_upsell(self, status_code):
        payload = {
            "error": f"EODHD API request failed with {status_code}.",
            "status_code": status_code,
        }

        with pytest.raises(ToolError) as exc:
            raise_on_api_error(payload)

        assert QUOTA_CONTROL_PANEL_URL not in str(exc.value)

    def test_successful_payload_is_untouched(self):
        assert raise_on_api_error({"close": 150.0}) is None


# ---------------------------------------------------------------------------
# version sync — the User-Agent is only useful if the version is truthful
# ---------------------------------------------------------------------------


class TestVersionSync:
    def test_matches_pyproject(self):
        pyproject = (REPO_ROOT / "pyproject.toml").read_text()
        match = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)

        assert match is not None
        assert match.group(1) == SERVER_VERSION

    def test_matches_manifest(self):
        manifest = json.loads((REPO_ROOT / "manifest.json").read_text())

        assert manifest["version"] == SERVER_VERSION
