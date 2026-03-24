# get_sentiment_data.py

import logging

from collections.abc import Iterable

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import coerce_date_param, validate_date_range
from app.config import EODHD_API_BASE
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)

def _normalize_symbols(symbols: Iterable[str]) -> str:
    # Turn a sequence like ["AAPL.US","BTC-USD.CC"] into "AAPL.US,BTC-USD.CC"
    return ",".join(s.strip() for s in symbols if s and str(s).strip())

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_sentiment_data(
        symbols: str,
        start_date: str | None = None,  # maps to 'from' (YYYY-MM-DD)
        end_date: str | None = None,  # maps to 'to'   (YYYY-MM-DD)
        fmt: str = "json",
        api_token: str | None = None,
    ) -> ResourceResponse:
        """

        Get aggregated sentiment scores for stocks based on news and social media analysis.
        Returns daily sentiment polarity, news buzz, and weighted scores for one or more tickers over a date range.
        Use when analyzing market mood, news impact, or sentiment-driven trading signals.
        For raw news articles, use get_company_news instead.
        For word frequency in news, use get_news_word_weights instead.

        Args:
            symbols (str): One or more comma-separated tickers (e.g., 'AAPL.US,BTC-USD.CC').
            start_date (str, optional): YYYY-MM-DD, maps to 'from'.
            end_date (str, optional): YYYY-MM-DD, maps to 'to'.
            fmt (str): 'json' (default). (XML not documented for this endpoint.)
            api_token (str, optional): Per-call override; env token used if omitted.

        Returns:
            Object keyed by ticker, each value with:
            - date (str): sentiment date
            - count (int): number of articles analyzed
            - normalized (float): normalized sentiment score
            - buzz (object): articlesInLastWeek, weeklyAverage, buzz
            - sentiment (object): bearishPercent, bullishPercent

        Examples:
            "Apple sentiment this month" → symbols="AAPL.US", start_date="2026-03-01", end_date="2026-03-06"
            "Bitcoin and Ethereum sentiment" → symbols="BTC-USD.CC,ETH-USD.CC"
            "Microsoft sentiment in Q4 2025" → symbols="MSFT.US", start_date="2025-10-01", end_date="2025-12-31"

        Demo:
            To test data structure, use the test API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        # Validate required
        if not symbols or not isinstance(symbols, str):
            raise ToolError("Parameter 'symbols' is required (comma-separated string).")

        if fmt != "json":
            raise ToolError("Only 'json' is supported for this endpoint.")

        start_date = coerce_date_param(start_date, "start_date")
        end_date = coerce_date_param(end_date, "end_date")
        validate_date_range(start_date, end_date)

        # Build URL
        url = f"{EODHD_API_BASE}/sentiments?fmt={fmt}&s={symbols}"
        if start_date:
            url += f"&from={start_date}"
        if end_date:
            url += f"&to={end_date}"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return format_json_response(data)
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
