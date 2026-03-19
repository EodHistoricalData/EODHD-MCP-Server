"""Structured response formatting for MCP tool outputs.

Returns API data as EmbeddedResource with mimeType="application/json"
to signal that content is structured data, not LLM instructions.
Mitigates prompt injection via API responses (R5-HI-11).
"""

import json
import re
from typing import Any

from mcp.types import EmbeddedResource, TextResourceContents
from pydantic import AnyUrl

JsonResponse = list[EmbeddedResource]

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


def format_json_response(data: Any) -> JsonResponse:
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
                uri=AnyUrl("eodhd://api/response"),
                mimeType="application/json",
                text=json.dumps(data, indent=2),
            ),
        )
    ]
