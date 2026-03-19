# get_mp_us_options_underlyings.py

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
    async def get_us_options_underlyings(
        page_offset: int | None = None,  # optional pagination (if supported server-side)
        page_limit: int | None = None,  # optional pagination (if supported server-side)
        api_token: str | None = None,
        fmt: str | None = "json",
    ) -> list:
        """

        [Marketplace] List all US stock and ETF ticker symbols that have listed options.
        Use to check whether a specific ticker has options data or to browse the full universe
        of optionable underlyings before querying contracts or EOD pricing.
        For available contracts on a specific ticker, use get_us_options_contracts.
        For options pricing data, use get_us_options_eod.
        Consumes 10 API calls per request.


        Returns:
            JSON object with:
            - meta (object): Contains total count, fields list, compact flag.
            - data (array of str): Ticker symbols that have options available (e.g. ['AAPL','MSFT',...]).
            - links.next (str|null): URL for next page, null if last page.

        Examples:
            "list all tickers that have options" → (no params)
            "which stocks have options available" → (no params)


        """
        base = f"{EODHD_API_BASE}/mp/unicornbay/options/underlying-symbols?1=1"
        base += _q("page[offset]", page_offset)
        base += _q("page[limit]", page_limit)
        if api_token:
            base += _q("api_token", api_token)
        # format
        if fmt:
            base += _q("fmt", fmt)

        data = await make_request(base)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))
        try:
            return format_json_response(data)
        except Exception:
            raise ToolError("Unexpected response format from API.")
