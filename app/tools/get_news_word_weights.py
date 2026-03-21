# get_news_word_weights.py

import re
from datetime import datetime

from app.api_client import make_request
from app.input_formatter import build_url
from app.response_formatter import format_json_response
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _valid_date(d: str | None) -> bool:
    if d is None:
        return True
    if not DATE_RE.match(d):
        return False
    try:
        datetime.strptime(d, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_news_word_weights(
        ticker: str,  # maps to 's'
        start_date: str | None = None,  # maps to filter[date_from]
        end_date: str | None = None,  # maps to filter[date_to]
        limit: int | None = None,  # maps to page[limit]
        fmt: str = "json",
        api_token: str | None = None,
    ) -> list:
        """

        Get top weighted keywords from news articles for a given stock ticker over a date range.
        Returns word frequency and importance scores, useful for identifying dominant themes and narratives in coverage.
        Use when analyzing what topics or terms dominate news about a company.
        For raw news articles, use get_company_news instead.
        For aggregated sentiment scores, use get_sentiment_data instead.

        Args:
            ticker (str): Symbol to analyze (e.g., 'AAPL.US'); mapped to 's'.
            start_date (str, optional): YYYY-MM-DD; mapped to filter[date_from].
            end_date (str, optional): YYYY-MM-DD; mapped to filter[date_to].
            limit (int, optional): Number of top words; mapped to page[limit].
            fmt (str): 'json' (default). (CSV/XML not documented for this endpoint.)
            api_token (str, optional): Per-call token override.

        Returns:
            Object with:
            - data (object): date-grouped records with word-weight mappings
            - meta (object): pagination metadata
            - links (object): pagination links (self, next, prev)

        Examples:
            "Top news keywords for Apple last month" → ticker="AAPL.US", start_date="2026-02-01", end_date="2026-02-28"
            "Nvidia word weights, top 20" → ticker="NVDA.US", limit=20
            "Amazon news themes in Q1 2026" → ticker="AMZN.US", start_date="2026-01-01", end_date="2026-03-06"


        """
        if not ticker or not isinstance(ticker, str):
            raise ToolError("Parameter 'ticker' is required (e.g., 'AAPL.US').")

        if fmt != "json":
            raise ToolError("Only 'json' is supported for this endpoint.")

        if not _valid_date(start_date):
            raise ToolError("'start_date' must be YYYY-MM-DD when provided.")
        if not _valid_date(end_date):
            raise ToolError("'end_date' must be YYYY-MM-DD when provided.")
        if start_date and end_date:
            if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
                raise ToolError("'start_date' cannot be after 'end_date'.")

        if limit is not None:
            if not isinstance(limit, int) or limit <= 0:
                raise ToolError("'limit' must be a positive integer when provided.")

        url = build_url(
            "news-word-weights",
            {
                "s": ticker,
                "fmt": fmt,
                "filter[date_from]": start_date,
                "filter[date_to]": end_date,
                "page[limit]": limit,
                "api_token": api_token,
            },
        )

        data = await make_request(url)

        try:
            return format_json_response(data)
        except Exception:
            raise ToolError("Unexpected response format from API.")
