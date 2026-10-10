# tests/auto/test_plan_gate_upsell.py
"""Tests for the plan-gated (HTTP 403) path.

EODHD answers 403 when the plan behind the key does not cover the data an endpoint
serves, and its body for it says "invalid API key" — which sends the user to inspect a
token that is fine. This server replaces that lead with what a 403 actually means, and
adds the packaging detail for the two endpoints sold outside the ordinary plans.

Covers:
  - 403 carries the plan sentence, ahead of the upstream text, with the status as a field
  - get_company_news and get_bulk_fundamentals add their own offer; other tools do not
  - no other status picks up the plan hint
  - the hints are statements, never instructions to the agent
  - PLAN_HINTS keys name tools that exist, and no endpoint reference contradicts the hint
"""

import pathlib

import pytest
from app.response_formatter import (
    PLAN_BULK_FUNDAMENTALS_URL,
    PLAN_GATED_HINT,
    PLAN_HINTS,
    PLAN_NEWS_URL,
    QUOTA_PRICING_URL,
    UpstreamToolError,
    raise_on_api_error,
)
from fastmcp.exceptions import ToolError

FORBIDDEN_403_BODY = "Invalid API key. Check your api_token parameter."

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def payload(**extra):
    return {
        "error": "EODHD API request failed with 403 Forbidden.",
        "status_code": 403,
        "text": FORBIDDEN_403_BODY,
        **extra,
    }


def message_for(**kwargs) -> str:
    with pytest.raises(ToolError) as exc:
        raise_on_api_error(payload(), **kwargs)
    return str(exc.value)


class TestPlanGateHint:
    def test_403_explains_the_plan_rather_than_the_key(self):
        message = message_for()

        assert PLAN_GATED_HINT in message
        assert QUOTA_PRICING_URL in message
        assert "get_user_details" in message  # how the agent finds out which plan the key is on

    def test_403_leads_with_our_hint_and_keeps_the_upstream_text_behind_it(self):
        # The upstream text is wrong about the cause, not useless: should EODHD ever answer
        # 403 for a second reason, the user gets our explanation AND the real one.
        message = message_for()

        assert message.index(PLAN_GATED_HINT) < message.index(FORBIDDEN_403_BODY)
        assert f"upstream={FORBIDDEN_403_BODY}" in message

    def test_status_travels_as_a_field(self):
        # The telemetry middleware files the call by this, not by reading the prose.
        with pytest.raises(UpstreamToolError) as exc:
            raise_on_api_error(payload())

        assert exc.value.status_code == 403

    def test_upstream_detail_fields_are_kept_too(self):
        with pytest.raises(ToolError) as exc:
            raise_on_api_error({"error": "403", "status_code": 403, "upstream_message": "Forbidden."})

        message = str(exc.value)
        assert "upstream=Forbidden." in message
        assert message.index(PLAN_GATED_HINT) < message.index("upstream=")


class TestPerToolOffers:
    def test_news_names_where_news_is_included(self):
        message = message_for(tool="get_company_news")

        assert PLAN_HINTS["get_company_news"] in message
        assert "All-In-One" in message
        assert "free plan" in message  # a Free key reaching this tool is not the usual case
        assert PLAN_NEWS_URL in message

    def test_bulk_fundamentals_names_extended_fundamentals_and_the_cheaper_route(self):
        message = message_for(tool="get_bulk_fundamentals")

        assert PLAN_HINTS["get_bulk_fundamentals"] in message
        assert "Extended Fundamentals" in message
        assert "support@eodhistoricaldata.com" in message  # not self-serve, so someone has to be asked
        assert "get_fundamentals_data" in message  # a few tickers do not need this subscription
        assert PLAN_BULK_FUNDAMENTALS_URL in message

    def test_the_offer_follows_the_generic_sentence(self):
        message = message_for(tool="get_company_news")

        assert message.index(PLAN_GATED_HINT) < message.index(PLAN_HINTS["get_company_news"])

    def test_a_tool_without_an_offer_gets_the_generic_sentence_alone(self):
        message = message_for(tool="get_eod_historical_data")

        assert PLAN_GATED_HINT in message
        for hint in PLAN_HINTS.values():
            assert hint not in message

    def test_no_tool_named_gets_the_generic_sentence_alone(self):
        message = message_for()

        for hint in PLAN_HINTS.values():
            assert hint not in message


class TestBoundaries:
    @pytest.mark.parametrize("status_code", [400, 401, 402, 404, 422, 429, 500])
    def test_other_statuses_carry_no_plan_hint(self, status_code):
        with pytest.raises(ToolError) as exc:
            raise_on_api_error(
                {"error": f"EODHD API request failed with {status_code}.", "status_code": status_code},
                tool="get_company_news",
            )

        message = str(exc.value)
        assert PLAN_GATED_HINT not in message
        assert PLAN_HINTS["get_company_news"] not in message

    def test_successful_payload_is_untouched(self):
        assert raise_on_api_error({"close": 150.0}, tool="get_company_news") is None


class TestVoice:
    def test_hints_are_written_as_statements_not_instructions(self):
        # An agent may parrot the text verbatim; a command reads absurd to the person on
        # the other end, a statement does not.
        for text in (PLAN_GATED_HINT, *PLAN_HINTS.values()):
            for imperative in ("Relay ", "Give the user", "Tell the user", "Ask the user", "do not retry"):
                assert imperative not in text


class TestStaysTrue:
    def test_every_plan_hint_names_a_tool_that_exists(self):
        for tool_name in PLAN_HINTS:
            assert (REPO_ROOT / "app" / "tools" / f"{tool_name}.py").is_file()

    def test_the_tools_with_an_offer_pass_their_name(self):
        # The dict is only reachable if the call site names the tool; a refactor that drops
        # the argument would leave these tools silently on the generic sentence.
        for tool_name in PLAN_HINTS:
            source = (REPO_ROOT / "app" / "tools" / f"{tool_name}.py").read_text()
            assert f'raise_on_api_error(data, tool="{tool_name}")' in source

    def test_no_endpoint_reference_calls_a_403_an_invalid_key(self):
        # The agent reads these files alongside the error. While they said "invalid API key",
        # they overrode the hint and sent the user back to check a token that was fine.
        offenders = [
            path.name
            for path in (REPO_ROOT / "app" / "resources" / "references").rglob("*.md")
            for line in path.read_text().splitlines()
            if line.startswith("| **403**") and "Invalid API key" in line
        ]

        assert offenders == []
