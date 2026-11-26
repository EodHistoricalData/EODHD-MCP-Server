# app/tools/get_etf_held_by.py


import logging

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, coerce_page_params, sanitize_ticker
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)

MAX_PAGE_LIMIT = 5000


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="ETF Held By (funds holding a security)", readOnlyHint=True))
    async def get_etf_held_by(
        ticker: str,  # the security that is looked up, e.g. NVDA or ASML.AS (not a fund)
        limit: int | str | None = None,  # page[limit]
        offset: int | str | None = None,  # page[offset]
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Find which US-listed ETFs hold a given security (reverse lookup), sorted by the weight of
        the security in each fund. Use when the user asks which ETFs own a stock, how widely a stock
        is held by funds, or which funds have the largest position in it.

        Beta API. Covers US-listed ETFs only, with positions from their latest SEC N-PORT filings.
        The ticker is the security, not a fund: US tickers ("NVDA", "XOM") and foreign tickers with
        an exchange suffix ("ASML.AS") are accepted. Costs 10 API calls per request. Requires the
        Fundamentals Data Feed or All-In-One plan. The demo token is rejected here (403).

        To see what one ETF holds, use get_etf_holdings.

        Args:
            ticker (str): Security ticker, e.g. "NVDA" or "ASML.AS".
            limit (int, optional): Funds per page, 1..5000 (default 100).
            offset (int, optional): Pagination offset, zero-based (default 0).
            api_token (str, optional): Per-call token override.

        Returns:
            JSON envelope {data, meta, links}:
            - data.security (obj): ticker, exchange, name
            - data.held_by_count (int): number of funds that hold the security
            - data.funds (list): ticker, name, weight (percent of the fund), shares, value_usd,
              report_date; sorted by weight descending. Empty list past the last page.
            - meta: total, offset, limit
            - links.next (str|null): relative URL of the next page without the token; null on the
              last page

        Notes:
            - Unknown ticker returns 404 (without a code on this endpoint).
            - 403 means the plan does not include this API, or the demo token was used.
            - limit above 5000 is rejected.

        Examples:
            "Which ETFs hold NVIDIA?" → get_etf_held_by(ticker="NVDA", limit=20)
            "Next page of funds holding Exxon" → get_etf_held_by(ticker="XOM", limit=100, offset=100)
        """
        symbol = sanitize_ticker(ticker, param_name="ticker")
        lim, off = coerce_page_params(limit, offset, max_limit=MAX_PAGE_LIMIT)

        url = build_url(
            f"etf/security/{symbol}/held-by",
            {"api_token": api_token, "page[limit]": lim, "page[offset]": off},
        )

        data = await make_request(url)

        return format_json_response(data)
