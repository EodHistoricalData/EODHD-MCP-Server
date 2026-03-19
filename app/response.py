"""Structured response formatting for MCP tool outputs.

Wrap tool results in MIME-typed MCP EmbeddedResource objects so clients can
distinguish structured JSON, plain text, and binary payloads from free-form
model text. This also reduces prompt-injection risk from upstream API data.
"""

import base64
import json
import re
from typing import Any

from mcp.types import BlobResourceContents, EmbeddedResource, TextResourceContents
from pydantic import AnyUrl

ResourceResponse = list[EmbeddedResource]
JsonResponse = ResourceResponse

# Zero-width spaces, RTL/LTR overrides, word joiners, BOM, and other invisible chars
_INVISIBLE_RE = re.compile("[\u200b-\u200f\u2028-\u202f\u2060-\u206f\ufeff]")


def _strip_invisible_chars(text: str) -> str:
    """Remove invisible Unicode characters that could be used for prompt injection."""
    return _INVISIBLE_RE.sub("", text)


def _sanitize_data(obj: Any) -> Any:
    """Recursively strip invisible Unicode chars from all string values."""
    if isinstance(obj, str):
        return _strip_invisible_chars(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_data(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_data(item) for item in obj]
    return obj


def _resource_uri(path: str) -> AnyUrl:
    return AnyUrl(f"eodhd://api/{path.lstrip('/')}")


def format_text_response(text: str, mime_type: str, *, resource_path: str = "response") -> ResourceResponse:
    """Return text data as an EmbeddedResource with an explicit MIME type."""
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
    """Return binary data as a base64-encoded EmbeddedResource."""
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
    """Return API data as JSON with application/json MIME type.

    Wraps the data in an MCP EmbeddedResource so that LLM clients
    see a ``mimeType="application/json"`` annotation, reducing the
    risk that injected text in field values (company names, headlines)
    is interpreted as instructions.
    """
    data = _sanitize_data(data)
    return [
        EmbeddedResource(
            type="resource",
            resource=TextResourceContents(
                uri=_resource_uri(resource_path),
                mimeType="application/json",
                text=json.dumps(data, indent=2),
            ),
        )
    ]
