# app/tools/get_sanctions_sources.py


import logging

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url
from app.response_formatter import (
    ResourceResponse,
    format_json_response,
    raise_on_api_error,
)

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Sanctions/OFAC: Sources", readOnlyHint=True))
    async def get_sanctions_sources(
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        List available sanctions data sources. Use when the user asks which sanctions lists or
        sources are available (e.g. OFAC), or wants to discover valid values for the 'source'
        parameter on other sanctions tools.

        Returns the available sanctions sources. This endpoint returns the full list and is not
        paginated.

        Args:
            api_token (str, optional): Per-call token override.


        Returns:
            JSON envelope {data, meta, links}. Each data item:
            - name (str): source name

        Examples:
            "List sanctions sources" → get_sanctions_sources()
        """
        url = build_url(
            "sanctions/sources",
            {"api_token": api_token},
        )

        data = await make_request(url)
        raise_on_api_error(data)

        return format_json_response(data)
