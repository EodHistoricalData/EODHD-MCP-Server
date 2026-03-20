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
