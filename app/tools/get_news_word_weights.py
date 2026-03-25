# app/tools/get_news_word_weights.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_query_param, build_url, coerce_date_param, sanitize_ticker, validate_date_range
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_news_word_weights(
        ticker: str,  # maps to 's'
        start_date: str | None = None,  # maps to filter[date_from]
        end_date: str | None = None,  # maps to filter[date_to]
        limit: int | None = None,  # maps to page[limit]
        fmt: str = "json",
        api_token: str | None = None,
    ) -> ResourceResponse:
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

        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        ticker = sanitize_ticker(ticker)

        if fmt != "json":
            raise ToolError("Only 'json' is supported for this endpoint.")

        start_date = coerce_date_param(start_date, "start_date")
        end_date = coerce_date_param(end_date, "end_date")
        validate_date_range(start_date, end_date)

        if limit is not None:
            if not isinstance(limit, int) or limit <= 0:
                raise ToolError("'limit' must be a positive integer when provided.")

        url = build_url(
            "news-word-weights",
            {
                "s": ticker,
                "fmt": fmt,
                "api_token": api_token,
            },
        )
        url += build_query_param("filter[date_from]", start_date)
        url += build_query_param("filter[date_to]", end_date)
        url += build_query_param("page[limit]", limit)

        data = await make_request(url)

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
