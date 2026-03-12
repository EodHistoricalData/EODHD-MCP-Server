"""Structured response formatting for MCP tool outputs.

Returns API data as EmbeddedResource with mimeType="application/json"
to signal that content is structured data, not LLM instructions.
Mitigates prompt injection via API responses (R5-HI-11).
"""

import json
from typing import Any

from mcp.types import EmbeddedResource, TextResourceContents
from pydantic import AnyUrl

JsonResponse = list[EmbeddedResource]


def format_json_response(data: Any) -> JsonResponse:
    """Return API data as JSON with application/json MIME type.

    Wraps the data in an MCP EmbeddedResource so that LLM clients
    see a ``mimeType="application/json"`` annotation, reducing the
    risk that injected text in field values (company names, headlines)
    is interpreted as instructions.
    """
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
