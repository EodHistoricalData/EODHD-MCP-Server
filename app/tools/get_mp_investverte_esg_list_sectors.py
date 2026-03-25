# app/tools/get_mp_investverte_esg_list_sectors.py


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
    async def get_mp_investverte_esg_list_sectors(
        fmt: str | None = "json",
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        [InvestVerte] List all sectors available in the ESG dataset.
        Returns an array of sector names with ESG coverage (e.g., "Airlines", "Aerospace & Defense").
        Use as a reference lookup before calling get_mp_investverte_esg_view_sector for detailed ESG data.
        Consumes 10 API calls per request.
        For company or country reference lists, use get_mp_investverte_esg_list_companies or list_countries.


        Returns:
            A JSON-formatted string containing an array of objects:
            [
              {"sector": "Aerospace & Defense"},
              {"sector": "Airlines"},
              ...
            ]

        Notes:
            - This endpoint lists all sectors covered by the Investverte ESG dataset.
            - Rate limits (Marketplace product):
                * 100,000 API calls per 24 hours
                * 1,000 API requests per minute
                * 1 API request = 10 API calls

        Examples:
            "List all ESG sectors" → (no params needed)
            "What sectors have ESG coverage?" → (no params needed)


        """
        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        # Base URL for Investverte sectors list
        url = build_url("mp/investverte/sectors", {"fmt": fmt, "api_token": api_token})

        data = await make_request(url)

        try:
            # Expected: list of {"sector": "..."}
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
