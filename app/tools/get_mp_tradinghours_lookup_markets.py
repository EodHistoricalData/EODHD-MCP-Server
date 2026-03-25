# app/tools/get_mp_tradinghours_lookup_markets.py

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
    async def get_mp_tradinghours_lookup_markets(
        q: str | None = None,  # free-form search term
        group: str | None = None,  # core, extended, all, allowed (default: all)
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        [TradingHours] Search for markets by name, MIC code, country, or free-form query.
        Use when the user asks to find a specific exchange or market by keyword (e.g. "Tokyo",
        "XNYS", "Germany"). Covers 900+ global trading schedules.
        To list all markets without searching, use get_mp_tradinghours_list_markets.
        For full details on a found market, pass its fin_id to get_mp_tradinghours_market_details.
        Consumes 10 API calls per request.

        Args:
            q (str, optional): Free-form search query (exchange name, market name, MIC,
                country). Omit to return all markets.
            group (str, optional): Filter results — 'core', 'extended', 'all', 'allowed'.
                Default: 'all'.
            api_token (str, optional): Per-call token override; env token used otherwise.


        Returns:
            JSON array of matching market objects, each with:
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
            - Over 900 different trading schedules tracked.
            - Omitting 'q' returns all markets (like list endpoint).

        Examples:
            "find NASDAQ market" → q="NASDAQ"
            "search for London Stock Exchange" → q="London Stock Exchange"
            "markets in Japan, core tier" → q="Japan", group="core"


        """
        if group is not None:
            group = group.strip().lower()
            if group not in ALLOWED_GROUPS:
                raise ToolError(f"Invalid 'group'. Allowed: {sorted(ALLOWED_GROUPS)}")

        url = build_url(
            "mp/tradinghours/markets/lookup",
            {
                "q": q.strip() if q else None,
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
