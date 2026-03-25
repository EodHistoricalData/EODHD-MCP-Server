# app/tools/get_mp_investverte_esg_view_company.py


import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, sanitize_ticker
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)

ALLOWED_FREQUENCIES = {"FY", "Q1", "Q2", "Q3", "Q4"}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_investverte_esg_view_company(
        symbol: str,  # e.g., "AAPL" or "000039.SZ"
        year: int | str | None = None,  # e.g., 2021
        frequency: str | None = None,  # one of ALLOWED_FREQUENCIES
        fmt: str | None = "json",
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        [InvestVerte] Get detailed ESG scores (E, S, G, and composite) for a specific company by symbol.
        Returns Environmental, Social, Governance, and combined ESG scores broken down by year and
        frequency (FY, Q1-Q4). Optionally filter by year and frequency. Consumes 10 API calls per request.
        Use get_mp_investverte_esg_list_companies first to discover available symbols.
        For country-level ESG, use get_mp_investverte_esg_view_country.
        For sector-level ESG, use get_mp_investverte_esg_view_sector.


        Returns:
            A JSON-formatted string with an array of objects, e.g.:

            [
              {
                "e": 58.97,
                "s": 68.66,
                "g": 65.21,
                "esg": 64.09,
                "year": 2021,
                "frequency": "FY"
              },
              ...
            ]

        Notes:
            - Year and frequency are optional; when omitted, all available
              years/frequencies for the symbol are returned.
            - Rate limits (Marketplace product):
                * 100,000 API calls per 24 hours
                * 1,000 API requests per minute
                * 1 API request = 10 API calls

        Examples:
            - /api/mp/investverte/esg/AAPL?year=2021&frequency=FY
            - /api/mp/investverte/esg/000039.SZ


        """
        symbol = sanitize_ticker(symbol, param_name="symbol")

        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        if frequency is not None and frequency not in ALLOWED_FREQUENCIES:
            raise ToolError(f"Invalid 'frequency'. Allowed: {sorted(ALLOWED_FREQUENCIES)}")

        if year is not None and not isinstance(year, (int, str)):
            raise ToolError("Parameter 'year' must be an integer or string representing a year, e.g., 2021.")

        # Base URL for Investverte company ESG endpoint
        url = build_url(
            f"mp/investverte/esg/{symbol}",
            {
                "fmt": fmt,
                "year": year,
                "frequency": frequency,
                "api_token": api_token,
            },
        )

        data = await make_request(url)

        try:
            # Expected: list of ESG entries for the company
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
