# get_mp_tradinghours_market_details.py

from urllib.parse import quote_plus

from app.api_client import make_request
from app.config import EODHD_API_BASE
from app.response import format_json_response
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def _q(key: str, val: str | int | None) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_tradinghours_market_details(
        fin_id: str,  # e.g. "us.nyse"
        api_token: str | None = None,  # per-call override
    ) -> list:
        """

        [TradingHours] Get detailed metadata for a specific market by its FinID. Use when asked
        about an exchange's timezone, MIC codes, asset types, weekend schedule, or holiday date range.
        Returns country, timezone (IANA), products traded, MIC/MIC extended, acronym, and more.
        Find the FinID first via get_mp_tradinghours_list_markets or get_mp_tradinghours_lookup_markets.
        For real-time open/closed status, use get_mp_tradinghours_market_status instead.
        Consumes 10 API calls per request.

        Args:
            fin_id (str): Market FinID, case-insensitive (e.g. 'us.nyse', 'gb.lse').
            api_token (str, optional): Per-call token override; env token used otherwise.


        Returns:
            JSON object with:
            - fin_id (str): Unique market identifier (e.g. 'us.nyse').
            - exchange (str): Exchange name.
            - market (str): Market name.
            - products (str): Traded product types.
            - timezone (str): IANA timezone identifier.
            - local_time (str): Current local time at the exchange.
            - regular (object): Regular session hours with open/close times.
            - pre_market (object|null): Pre-market session hours, if applicable.
            - post_market (object|null): Post-market session hours, if applicable.
            - holidays (array): Upcoming holidays with date, name, and schedule impact.

        Notes:
            - Marketplace product: 10 API calls per request.
            - Returns IANA timezone identifiers.

        Examples:
            "NYSE market details" → fin_id="us.nyse"
            "London Stock Exchange info" → fin_id="gb.lse"
            "Tokyo Stock Exchange details" → fin_id="jp.jpx"


        """
        if not fin_id or not isinstance(fin_id, str):
            raise ToolError("Parameter 'fin_id' is required (e.g. 'us.nyse').")

        url = f"{EODHD_API_BASE}/mp/tradinghours/markets/details?1=1"
        url += _q("fin_id", fin_id.strip())
        if api_token:
            url += _q("api_token", api_token)

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return format_json_response(data)
        except Exception:
            raise ToolError("Unexpected response format from API.")
