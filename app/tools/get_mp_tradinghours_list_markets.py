# app/tools/get_mp_tradinghours_list_markets.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)

ALLOWED_GROUPS = {"core", "extended", "all", "allowed"}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_tradinghours_list_markets(
        group: str | None = None,  # core, extended, all, allowed (default: all)
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        [TradingHours] List all tracked global markets and exchanges. Use as the starting point
        to browse available markets before looking up details or checking status.
        Returns FinID, exchange name, MIC code, asset type, and group for each market.
        Filter by group: 'core' (24 G20+ markets), 'extended', 'all', or 'allowed' (your tier).
        To search markets by name/country, use get_mp_tradinghours_lookup_markets.
        For detailed info on one market, use get_mp_tradinghours_market_details.
        Consumes 10 API calls per request.

        Args:
            group (str, optional): Filter markets — 'core' (G20+), 'extended' (global equities),
                'all' (equities + derivatives), 'allowed' (your tier). Default: 'all'.
            api_token (str, optional): Per-call token override; env token used otherwise.


        Returns:
            JSON array of market objects, each with:
            - fin_id (str): Unique market identifier (e.g. 'us.nyse').
            - exchange (str): Exchange name.
            - market (str): Market name.
            - products (str): Traded product types.
            - country (str): Country name.
            - country_code (str): ISO country code.
            - city (str): City where exchange is located.
            - timezone (str): IANA timezone identifier.
            - timezone_abbr (str): Timezone abbreviation.
            - mic (str): Market Identifier Code (ISO 10383).
            - mic_o (str): Operating MIC.

        Notes:
            - Marketplace product: 10 API calls per request.
            - Core tier: 24 G20+ markets.

        Examples:
            "list all tracked markets" → (no params)
            "show only G20 core markets" → group="core"
            "all equity and derivative markets" → group="all"


        """
        if group is not None:
            group = group.strip().lower()
            if group not in ALLOWED_GROUPS:
                raise ToolError(f"Invalid 'group'. Allowed: {sorted(ALLOWED_GROUPS)}")

        url = build_url(
            "mp/tradinghours/markets",
            {
                "group": group,
                "api_token": api_token,
            },
        )

        data = await make_request(url)

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
