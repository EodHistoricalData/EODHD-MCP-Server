# app/tools/get_mp_indices_list.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_indices_list(
        fmt: str = "json",  # API returns JSON; expose for symmetry
        api_token: str | None = None,  # per-call override (else env EODHD_API_KEY)
    ) -> ResourceResponse:
        """

        [Marketplace] List all available S&P and Dow Jones indices with end-of-day details.
        Use when asked to browse or enumerate major stock market indices, or to find an index
        symbol before fetching its components with mp_index_components.
        Covers 100+ indices including S&P 500, Dow Jones, and sector indices.
        For components/constituents of a specific index, use mp_index_components.
        Consumes 10 API calls per request.

        Args:
          - fmt: 'json' (default). (CSV is not documented; keep JSON only.)
          - api_token: optional override API token


        Returns:
            JSON array of objects, each with:
            - code (str): Index ticker code (e.g. 'GSPC.INDX').
            - name (str): Index name (e.g. 'S&P 500').
            - exchange (str): Exchange identifier.
            - currency (str): Currency code (e.g. 'USD').

        Examples:
            "show all S&P and Dow Jones indices" → (no params)
            "list available market indices with details" → (no params)


        """
        fmt = (fmt or "json").lower()
        if fmt != "json":
            raise ToolError("Only JSON is supported for this endpoint.")

        url = build_url("mp/unicornbay/spglobal/list", {"fmt": "json", "api_token": api_token})

        data = await make_request(url)

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected JSON response format from API.") from e
