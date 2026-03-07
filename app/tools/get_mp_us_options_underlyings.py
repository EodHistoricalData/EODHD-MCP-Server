#get_mp_us_options_underlyings.py

import json
from typing import Optional, Union
from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def _q(key: str, val: Optional[Union[str, int]]) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_us_options_underlyings(
        page_offset: Optional[int] = None,  # optional pagination (if supported server-side)
        page_limit: Optional[int] = None,   # optional pagination (if supported server-side)
        api_token: Optional[str] = None,
        fmt: Optional[str] = "json",
    ) -> str:
        """
        [Marketplace] List all US stock and ETF ticker symbols that have listed options.
        Use to check whether a specific ticker has options data or to browse the full universe
        of optionable underlyings before querying contracts or EOD pricing.
        For available contracts on a specific ticker, use get_us_options_contracts.
        For options pricing data, use get_us_options_eod.
        Consumes 10 API calls per request.
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
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
