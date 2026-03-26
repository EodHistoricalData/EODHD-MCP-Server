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

ResourceResponse = list[EmbeddedResource]
JsonResponse = ResourceResponse

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

    raise ToolError(" | ".join(message_parts))


def format_text_response(text: str, mime_type: str, *, resource_path: str = "response") -> ResourceResponse:
    """Return textual API data as an EmbeddedResource with its MIME type."""
    return [
        EmbeddedResource(
            type="resource",
            resource=TextResourceContents(
                uri=_resource_uri(resource_path),
                mimeType=mime_type,
                text=_strip_invisible_chars(text),
            ),
        )
    ]


def format_binary_response(data: bytes, mime_type: str, *, resource_path: str = "response") -> ResourceResponse:
    """Return binary API data as a base64-encoded EmbeddedResource."""
    return [
        EmbeddedResource(
            type="resource",
            resource=BlobResourceContents(
                uri=_resource_uri(resource_path),
                mimeType=mime_type,
                blob=base64.b64encode(data).decode("ascii"),
            ),
        )
    ]


def format_json_response(data: Any, *, resource_path: str = "response") -> JsonResponse:
    """Return JSON-like API data as application/json."""
    raise_on_api_error(data)
    if data is None:
        raise ToolError("No response from API.")
    sanitized = _sanitize_data(data)
    return [
        EmbeddedResource(
            type="resource",
            resource=TextResourceContents(
                uri=_resource_uri(resource_path),
                mimeType="application/json",
                text=json.dumps(sanitized, indent=2),
            ),
        )
    ]
