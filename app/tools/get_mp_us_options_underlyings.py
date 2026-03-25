# app/tools/get_mp_us_options_underlyings.py

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
    async def get_us_options_underlyings(
        page_offset: int | None = None,  # optional pagination (if supported server-side)
        page_limit: int | None = None,  # optional pagination (if supported server-side)
        api_token: str | None = None,
        fmt: str | None = "json",
    ) -> ResourceResponse:
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
        url = build_url(
            "mp/unicornbay/options/underlying-symbols",
            {
                "page[offset]": page_offset,
                "page[limit]": page_limit,
                "api_token": api_token,
                "fmt": fmt,
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
