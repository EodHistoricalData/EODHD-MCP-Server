# app/response_formatter.py
"""Structured response formatting for MCP tool outputs.

This module keeps API payloads typed as MCP resources and applies only
minimal text sanitization:
- textual payloads have invisible control characters stripped
- binary payloads are passed through unchanged
"""

import base64
import json
import re
from typing import Any

from fastmcp.exceptions import ToolError
from mcp.types import BlobResourceContents, EmbeddedResource, TextResourceContents
from pydantic import AnyUrl

from . import quota

ResourceResponse = list[EmbeddedResource]
JsonResponse = ResourceResponse


class UpstreamToolError(ToolError):
    """A ToolError that still knows the upstream HTTP status behind it.

    The telemetry middleware used to recover that status by running a regex over the
    message text. That worked only while this server wrote the whole message itself,
    and it no longer does: the upstream response is kept in there now, so a reply that
    happened to contain "status_code=402" would have been filed as a spent quota. The
    code travels as a field, and nobody has to read prose to classify a call.

    Subclass rather than a new type, so every existing `except ToolError` still catches
    it and tools that only render the message are untouched.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


# EODHD returns HTTP 402 from one place only — the daily-quota rate limiters
# (App\Services\RateLimit\*) — so 402 always means "daily API-call quota spent".
# Its upstream text sends the user to support, which is a dead end: both ways out are
# self-serve. On 402 that text is replaced by this hint rather than stacked next to it,
# so the agent does not relay "contact support" and "support is not needed" together.
# Phrased as statements, never as instructions to the agent: an agent that parrots the
# text verbatim then still reads as a sensible message to the person on the other end.
QUOTA_CONTROL_PANEL_URL = "https://eodhd.com/cp/dashboard"
QUOTA_PRICING_URL = "https://eodhd.com/pricing"

QUOTA_EXHAUSTED_HINT = (
    "The daily API-call quota for this EODHD API key is used up. It resets on its own at "
    "00:00 UTC, and a retry before then fails again. Support does not need to be contacted: "
    "on a paid plan there are two self-serve options — extra API calls (a one-off top-up, "
    "spent automatically whenever the daily limit is reached, and it does not expire) and "
    f"raising the daily limit itself, both in the Daily usage panel of {QUOTA_CONTROL_PANEL_URL}; "
    "on the free plan extra API calls can be bought in that same panel, but raising the daily "
    f"limit requires moving to a paid plan ({QUOTA_PRICING_URL}). Which of the two applies "
    "depends on the plan this key is on, which the get_user_details tool reports without "
    "consuming quota."
)

# Zero-width spaces, bidi overrides, word joiners, BOM, and similar invisible
# formatting characters that can hide instruction-like text from readers.
_INVISIBLE_RE = re.compile("[\u200b-\u200f\u2028-\u202f\u2060-\u206f\ufeff]")


def _strip_invisible_chars(text: str) -> str:
    """Remove invisible Unicode formatting characters from text."""
    return _INVISIBLE_RE.sub("", text)


def _sanitize_data(obj: Any) -> Any:
    """Recursively sanitize string values in JSON-like data."""
    if isinstance(obj, str):
        return _strip_invisible_chars(obj)
    if isinstance(obj, dict):
        return {key: _sanitize_data(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_data(item) for item in obj]
    return obj


def _resource_uri(path: str) -> AnyUrl:
    return AnyUrl(f"eodhd://api/{path.lstrip('/')}")


def _pick_error_text(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str):
            value = value.strip()
            if value:
                return value
    return None


def _extract_error_context(data: dict[str, Any]) -> tuple[str | None, str | None]:
    error_code = _pick_error_text(data, "error_code", "code", "errorCode")
    detail = _pick_error_text(
        data,
        "upstream_message",
        "errorMessage",
        "message",
        "detail",
        "description",
        "error_description",
    )

    response_text = data.get("text")
    if isinstance(response_text, str):
        try:
            parsed = json.loads(response_text)
        except ValueError:
            parsed = None

        if isinstance(parsed, dict):
            error_code = error_code or _pick_error_text(parsed, "code", "error_code", "errorCode")
            detail = detail or _pick_error_text(
                parsed,
                "errorMessage",
                "message",
                "detail",
                "description",
                "error_description",
            )
            if detail is None:
                nested_error = parsed.get("error")
                if isinstance(nested_error, str):
                    nested_error = nested_error.strip()
                    if nested_error:
                        detail = nested_error

    return error_code, detail


def is_client_error(data: Any) -> bool:
    """True when make_request() returned a 4xx error payload.

    Tools use this to decide whether an alternative request shape is worth trying
    before the error is surfaced to the agent.
    """
    if not isinstance(data, dict) or not data.get("error"):
        return False

    status_code = data.get("status_code")

    return isinstance(status_code, int) and 400 <= status_code < 500


def raise_on_api_error(data: Any) -> None:
    """Raise ToolError when make_request() returned a structured API error."""
    if not isinstance(data, dict):
        return

    error = data.get("error")
    if not error:
        return

    message_parts = [str(error)]

    status_code = data.get("status_code")
    if status_code is not None:
        message_parts.append(f"status_code={status_code}")

    # The hint above is built on an assumption about someone else's system — that 402
    # comes from the daily-quota limiters and nowhere else. That assumption lives in our
    # code and the system it describes is theirs to change, so the upstream text is kept
    # as a subordinate detail rather than dropped: should a second source of 402 ever
    # appear, the user gets a confident explanation AND the real one, not only the wrong
    # one. Our sentence already says support is not needed, so a relayed "contact
    # support" below it does not read as advice.
    if status_code == 402:
        message_parts.append(QUOTA_EXHAUSTED_HINT)

        _, upstream_detail = _extract_error_context(data)
        upstream = upstream_detail or str(data.get("text") or "").strip()
        if upstream and upstream != str(error):
            message_parts.append(f"upstream={upstream}")

        raise UpstreamToolError(" | ".join(message_parts), status_code)

    error_code, detail = _extract_error_context(data)
    if error_code:
        message_parts.append(f"code={error_code}")

    if detail and detail != str(error):
        message_parts.append(detail)

    if not detail:
        response_text = data.get("text")
        if response_text:
            fallback = str(response_text).strip()
            if fallback and fallback != str(error):
                message_parts.append(fallback)

    raise UpstreamToolError(" | ".join(message_parts), status_code)


def format_text_response(text: str, mime_type: str, *, resource_path: str = "response") -> ResourceResponse:
    """Return textual API data as an EmbeddedResource with its MIME type."""
    return _with_quota_notice(
        [
            EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri=_resource_uri(resource_path),
                    mimeType=mime_type,
                    text=_strip_invisible_chars(text),
                ),
            )
        ]
    )


def format_binary_response(data: bytes, mime_type: str, *, resource_path: str = "response") -> ResourceResponse:
    """Return binary API data as a base64-encoded EmbeddedResource."""
    return _with_quota_notice(
        [
            EmbeddedResource(
                type="resource",
                resource=BlobResourceContents(
                    uri=_resource_uri(resource_path),
                    mimeType=mime_type,
                    blob=base64.b64encode(data).decode("ascii"),
                ),
            )
        ]
    )


def format_json_response(data: Any, *, resource_path: str = "response") -> JsonResponse:
    """Return JSON-like API data as application/json."""
    raise_on_api_error(data)
    if data is None:
        raise ToolError("No response from API.")
    sanitized = _sanitize_data(data)
    return _with_quota_notice(
        [
            EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri=_resource_uri(resource_path),
                    mimeType="application/json",
                    text=json.dumps(sanitized, indent=2),
                ),
            )
        ]
    )


def _with_quota_notice(response: ResourceResponse) -> ResourceResponse:
    """Carry a pending quota notice alongside the data, as its own resource.

    It rides on whatever tool happened to run, which is the point: the user learns the
    quota is running low during the work, without having to ask. Every formatter drains
    it, so a notice raised during a CSV or image request is delivered there rather than
    waiting for the next JSON one.
    """
    notice = quota.take_pending_note()
    if not notice:
        return response

    return [
        *response,
        EmbeddedResource(
            type="resource",
            resource=TextResourceContents(
                uri=_resource_uri("quota-notice"),
                mimeType="text/plain",
                text=notice,
            ),
        ),
    ]
