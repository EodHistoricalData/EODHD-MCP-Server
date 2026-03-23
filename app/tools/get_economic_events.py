# get_economic_events.py

from app.api_client import make_request
from app.config import EODHD_API_BASE
from app.input_formatter import build_query_param
from app.response_formatter import ResourceResponse, format_json_response, format_text_response
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

ALLOWED_COMPARISON = {None, "mom", "qoq", "yoy"}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_economic_events(
        start_date: str | None = None,  # maps to from= (YYYY-MM-DD)
        end_date: str | None = None,  # maps to to=   (YYYY-MM-DD)
        country: str | None = None,  # ISO-3166 alpha-2 (e.g., US, GB, DE)
        comparison: str | None = None,  # mom | qoq | yoy
        type: str | None = None,  # free text, e.g. "House Price Index"
        offset: int = 0,  # 0..1000 (default 0)
        limit: int = 50,  # 0..1000 (default 50)
        fmt: str | None = "json",  # json (default) | csv (if supported)
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch macroeconomic calendar events such as GDP, CPI, employment, and interest rate releases.
        Returns scheduled and past economic indicators with actual, estimate, and previous values.
        Covers global economies; filter by country (ISO-2), date range, comparison period (mom/qoq/yoy), and event type.
        Use when the user asks about economic calendar, macro releases, or upcoming government data publications.
        This tool covers macro events only -- for company-level earnings dates, use get_upcoming_earnings.


        Returns:
            Array of events, each with:
            - type (str): event category
            - country (str): ISO-3166 alpha-2 country code
            - date (str): event datetime
            - actual (float|null): actual value
            - previous (float|null): previous period value
            - estimate (float|null): consensus estimate
            - change (float|null): absolute change
            - changePercentage (float|null): percentage change
            - event (str): event name/description

        Examples:
            "US economic events this week" → country="US", start_date="2026-03-02", end_date="2026-03-06"
            "German GDP year-over-year" → country="DE", comparison="yoy", type="GDP"
            "All events in March 2026, first 200" → start_date="2026-03-01", end_date="2026-03-31", limit=200


        Demo:
            To test data structure, use the test API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        # --- validate ---
        if comparison not in ALLOWED_COMPARISON:
            raise ToolError("Invalid 'comparison'. Allowed: 'mom', 'qoq', 'yoy' or omit.")
        if not isinstance(offset, int) or not (0 <= offset <= 1000):
            raise ToolError("'offset' must be an integer between 0 and 1000.")
        if not isinstance(limit, int) or not (0 <= limit <= 1000):
            raise ToolError("'limit' must be an integer between 0 and 1000.")
        if country is not None and (not isinstance(country, str) or len(country.strip()) != 2):
            raise ToolError("'country' must be a 2-letter ISO code (e.g., 'US').")

        # --- build URL ---
        # Example:
        # /economic-events?api_token=XXX&fmt=json&from=2025-01-05&to=2025-01-06&country=US&limit=1000
        url = f"{EODHD_API_BASE}/economic-events?1=1"
        url += build_query_param("from", start_date)
        url += build_query_param("to", end_date)
        url += build_query_param("country", country.upper() if country else None)
        url += build_query_param("comparison", comparison)
        url += build_query_param("type", type)
        url += build_query_param("offset", offset)
        url += build_query_param("limit", limit)
        url += build_query_param("fmt", fmt or "json")
        if api_token:
            url += build_query_param("api_token", api_token)  # otherwise appended by make_request

        # --- request ---
        output_fmt = (fmt or "json").lower()
        data = await make_request(url, response_mode="text" if output_fmt == "csv" else "json")

        # --- return/normalize ---
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        if output_fmt == "csv":
            if not isinstance(data, str):
                raise ToolError("Unexpected CSV response format from API.")
            return format_text_response(data, "text/csv", resource_path="economic-events/events.csv")

        return format_json_response(data)
