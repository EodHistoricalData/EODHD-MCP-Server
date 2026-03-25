# app/tools/get_company_news.py

import logging
import re

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, coerce_date_param, sanitize_ticker, validate_date_range
from app.response_formatter import ResourceResponse, format_json_response, format_text_response, raise_on_api_error

logger = logging.getLogger(__name__)

ALLOWED_FMT = {"json", "xml"}
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _sanitize_articles(data: list) -> list:
    """Strip HTML tags from title/content fields before returning news content."""
    for article in data:
        if not isinstance(article, dict):
            continue
        for field in ("title", "content"):
            value = article.get(field)
            if isinstance(value, str):
                article[field] = _HTML_TAG_RE.sub("", value)
    return data


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_company_news(
        ticker: str | None = None,  # maps to 's'
        tag: str | None = None,  # maps to 't'
        start_date: str | None = None,  # maps to 'from' (YYYY-MM-DD)
        end_date: str | None = None,  # maps to 'to' (YYYY-MM-DD)
        limit: int = 50,  # 1..1000 (API default 50)
        offset: int = 0,  # default 0
        fmt: str = "json",  # 'json' or 'xml' (API default json)
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch financial news articles for a stock ticker or topic tag within a date range.
        Returns full article objects with title, content, URL, date, and related tickers.
        Use when the user asks for news headlines, recent articles, or press coverage about a company or sector.
        For aggregated sentiment scores derived from news, use get_sentiment_data instead.
        For keyword frequency analysis in news, use get_news_word_weights instead.

        Args:
            ticker (str, optional): SYMBOL.EXCHANGE_ID (e.g., 'AAPL.US'). Mapped to 's'.
            tag (str, optional): Topic tag (e.g., 'technology'). Mapped to 't'.
            start_date (str, optional): YYYY-MM-DD. Mapped to 'from'.
            end_date (str, optional): YYYY-MM-DD. Mapped to 'to'.
            limit (int): 1..1000 (default 50).
            offset (int): >= 0 (default 0).
            fmt (str): 'json' or 'xml' (default 'json').
            api_token (str, optional): Per-call token override; env token used if omitted.

        Returns:
            Array of articles, each with:
            - date (str): publication datetime ISO 8601
            - title (str): headline
            - content (str): full article text
            - link (str): source URL
            - symbols (list[str]): related ticker symbols
            - tags (list[str]): topic tags
            - sentiment (object): title/content/ner polarity and neg/neu/pos scores

        Examples:
            "Apple news last week" → ticker="AAPL.US", start_date="2026-02-27", end_date="2026-03-06"
            "Crypto news, 50 results" → tag="crypto", limit=50
            "Tesla news in February 2026, first 10" → ticker="TSLA.US", start_date="2026-02-01", end_date="2026-02-28", limit=10

        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        # --- Validate required conditions ---
        if isinstance(ticker, str) and not ticker.strip():
            ticker = None
        elif ticker is not None:
            ticker = sanitize_ticker(ticker)

        if not ticker and not tag:
            raise ToolError("Provide at least one of 'ticker' (s) or 'tag' (t).")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        start_date = coerce_date_param(start_date, "start_date")
        end_date = coerce_date_param(end_date, "end_date")
        validate_date_range(start_date, end_date)

        if not isinstance(limit, int) or not (1 <= limit <= 1000):
            raise ToolError("'limit' must be an integer between 1 and 1000.")
        if not isinstance(offset, int) or offset < 0:
            raise ToolError("'offset' must be a non-negative integer.")

        # --- Build URL per docs ---
        url = build_url(
            "news",
            {
                "fmt": fmt,
                "limit": limit,
                "offset": offset,
                "s": ticker,
                "t": tag,
                "from": start_date,
                "to": end_date,
                "api_token": api_token,
            },
        )

        # --- Request ---
        data = await make_request(url, response_mode="text" if fmt == "xml" else "json")
        raise_on_api_error(data)

        # --- Normalize / return ---

        if fmt == "xml":
            if not isinstance(data, str):
                raise ToolError("Unexpected XML response format from API.")
            return format_text_response(data, "application/xml", resource_path="news/feed.xml")

        if isinstance(data, list):
            data = _sanitize_articles(data)

        return format_json_response(data)
