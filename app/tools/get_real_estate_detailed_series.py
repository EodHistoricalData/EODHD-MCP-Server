# app/tools/get_real_estate_detailed_series.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, sanitize_country_code
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Real Estate: Detailed Series Catalog", readOnlyHint=True))
    async def get_real_estate_detailed_series(
        code: str,
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        List the catalogue of Detailed Property Prices (DPP) series available for a country
        in the BIS Real Estate Data API.

        Use this to discover the exact covered-area, property-type, and vintage combinations
        you can request from get_real_estate_detailed_prices. This is a parameterless
        catalogue endpoint (JSON only — fmt=csv is not honoured). Discover available country
        codes with get_real_estate_countries. Consumes 5 API calls per request.

        The endpoint returns the country's whole series catalogue in one response — it has no
        pagination upstream. The catalogue is small (at most a couple of dozen series per
        country), so the response stays well inside client limits.

        Args:
            code (str): ISO alpha-2 country code, case-insensitive (e.g. 'US', 'us').
            api_token (str, optional): Per-call token override. If not provided, env token is used.

        Returns:
            Envelope with:
            - data (array): each item with
                - covered_area (str), covered_area_label (str)
                - property_type (str), property_type_label (str)
                - vintage (str), vintage_label (str)
                - compiling_org (str)
                - priced_unit (str)
                - seasonal_adj (str)
                - unit_measure (str), unit_measure_label (str)
                - title (str): human-readable series title
            - meta (object): { country_code, total }

        Examples:
            "What detailed real estate series does the US have?" → get_real_estate_detailed_series(code="US")
        """
        code = _normalize_country_code(code)

        url = build_url(
            f"real-estate/{code}/detailed/series",
            {"api_token": api_token},
        )

        data = await make_request(url)

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e


def _normalize_country_code(code: str) -> str:
    """Sanitize and upper-case an ISO alpha-2 country code (case-insensitive)."""
    return sanitize_country_code(code)
