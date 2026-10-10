# app/tools/get_sanctions_programs.py


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
    @mcp.tool(annotations=ToolAnnotations(title="Sanctions/OFAC: Programs", readOnlyHint=True))
    async def get_sanctions_programs(
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        List sanctions programs with entity counts. Use when the user asks which sanctions
        programs exist, how many entities are under each program, or wants to browse available
        programs.

        Returns each sanctions program and the number of entities listed under it. This endpoint
        returns the full list and is not paginated.

        Args:
            api_token (str, optional): Per-call token override.


        Returns:
            JSON envelope {data, meta, links}. Each data item:
            - program (str): sanctions program
            - count (int): number of entities under the program

        Examples:
            "List sanctions programs" → get_sanctions_programs()
        """
        url = build_url(
            "sanctions/programs",
            {"api_token": api_token},
        )

        data = await make_request(url)
        raise_on_api_error(data)

        return format_json_response(data)
