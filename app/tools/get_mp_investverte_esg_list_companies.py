# app/tools/get_mp_investverte_esg_list_companies.py


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
    async def get_mp_investverte_esg_list_companies(
        fmt: str | None = "json",
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        [InvestVerte] List all companies available in the ESG dataset.
        Returns an array of symbol/name pairs for every company with ESG coverage.
        Use as a reference lookup before calling get_mp_investverte_esg_view_company for detailed ESG scores.
        Consumes 10 API calls per request.
        For country or sector reference lists, use get_mp_investverte_esg_list_countries or list_sectors.


        Returns:
            A JSON-formatted string containing an array of objects:
            [
              {"symbol": "000001.SZ", "name": "Ping An Bank Co., Ltd."},
              {"symbol": "000002.SZ", "name": "China Vanke Co., Ltd."},
              ...
            ]

        Notes:
            - This endpoint lists all companies covered by the Investverte ESG dataset.
            - Rate limits (Marketplace product):
                * 100,000 API calls per 24 hours
                * 1,000 API requests per minute
                * 1 API request = 10 API calls

        Examples:
            "List all ESG companies" → (no params needed)
            "Which companies have ESG data?" → (no params needed)


        """
        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        # Base URL for Investverte companies list
        url = build_url("mp/investverte/companies", {"fmt": fmt, "api_token": api_token})

        data = await make_request(url)

        try:
            # Expected: list of {"symbol": ..., "name": ...}
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
