# app/tools/get_earnings_trends.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def _normalize_symbols(symbols: str | list[str] | None) -> str | None:
    if symbols is None:
        return None
    if isinstance(symbols, str):
        s = symbols.strip()
        return s if s else None
    if isinstance(symbols, list):
        flat = [str(x).strip() for x in symbols if str(x).strip()]
        return ",".join(flat) if flat else None
    return None


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_earnings_trends(
        symbols: str | list[str],  # REQUIRED by API: 'AAPL.US' or ['AAPL.US','MSFT.US']
        fmt: str = "json",  # Trends are JSON-only (kept for consistency)
        api_token: str | None = None,  # per-call override (else uses env EODHD_API_KEY)
    ) -> ResourceResponse:
        """

        Get earnings trend data including EPS/revenue estimates, analyst revisions, and growth projections for specific stocks.
        Returns quarterly and annual consensus estimates, number of analysts, and revision history.
        Requires explicit symbol(s). Each request consumes ~10 API calls.
        Use when the user asks about earnings expectations, analyst estimate changes, or EPS growth trends.
        For earnings report dates and calendar, use get_upcoming_earnings instead.

        Returns:
            Array of trend records, each with:
            - code (str): ticker symbol
            - date (str): report date
            - period (str): fiscal period (e.g. '+1y', '0q')
            - growth (float|null): expected growth rate
            - earningsEstimate (object): avg, low, high, yearAgoEps, numberOfAnalysts, growth
            - revenueEstimate (object): avg, low, high, yearAgoRevenue, numberOfAnalysts, growth
            - epsTrend (object): current, 7daysAgo, 30daysAgo, 60daysAgo, 90daysAgo
            - epsRevisions (object): upLast7days, upLast30days, downLast7days, downLast30days

        Examples:
            "Apple earnings trend" → symbols="AAPL.US"
            "Compare Tesla and Nvidia earnings trends" → symbols="TSLA.US,NVDA.US"


        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        sym_param = _normalize_symbols(symbols)
        if not sym_param:
            raise ToolError("Parameter 'symbols' is required (e.g., 'AAPL.US' or ['AAPL.US','MSFT.US']).")

        url = build_url(
            "calendar/trends",
            {
                "symbols": sym_param,
                "fmt": (fmt or "json").lower(),
                "api_token": api_token,
            },
        )

        data = await make_request(url)

        try:
            return format_json_response(data)
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
