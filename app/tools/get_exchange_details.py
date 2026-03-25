# app/tools/get_exchange_details.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, coerce_date_param, sanitize_exchange, validate_date_range
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_exchange_details(
        exchange_code: str,  # e.g., "US", "LSE", "XETRA"
        start_date: str | None = None,  # maps to 'from' (YYYY-MM-DD)
        end_date: str | None = None,  # maps to 'to'   (YYYY-MM-DD)
        fmt: str = "json",  # API supports json (we gate to json here)
        api_token: str | None = None,  # per-call token override
    ) -> ResourceResponse:
        """

        Retrieve detailed metadata for a single exchange: trading hours, timezone, open/closed
        status, holidays, and ticker counts. Use when the user asks about exchange schedules,
        market holidays, or whether an exchange is currently open.

        Returns timezone, isOpen flag, trading hours (open/close with UTC equivalents, working
        days, lunch breaks), exchange holidays (bank and official, ~6 months window), and
        ticker statistics (active, updated today, previous day).

        For the list of all exchanges, use get_exchanges_list.
        For tickers on an exchange, use get_exchange_tickers.

        Args:
            exchange_code (str): Exchange code (e.g., 'US', 'LSE', 'XETRA').
            start_date (str, optional): YYYY-MM-DD; filter holidays from this date.
            end_date (str, optional): YYYY-MM-DD; filter holidays up to this date.
            fmt (str): 'json' only (default).
            api_token (str, optional): Per-call token override (env token otherwise).

        Returns:
            Object with:
            - Name (str): exchange full name
            - Code (str): exchange code
            - OperatingMIC (str): ISO 10383 operating MIC
            - Country (str): country name
            - Currency (str): primary currency code
            - CountryISO2 (str): alpha-2 country code
            - CountryISO3 (str): alpha-3 country code
            - Timezone (str): IANA timezone (e.g. "America/New_York")
            - isOpen (bool): whether the exchange is currently open
            - tradingHours (object): open, close, UTC equivalents, working days, lunch hours
            - ExchangeHolidays (array): holiday objects with Name, Date, Type (bank/official)
            - ActiveTickers (int): tickers active in last 2 months
            - UpdatedTickers (int): tickers updated today
            - PreviousDayUpdatedTickers (int): tickers updated previous day

        Examples:
            "Is the US market open right now?" → get_exchange_details(exchange_code="US")
            "LSE trading hours and timezone" → get_exchange_details(exchange_code="LSE")
            "XETRA holidays in Q1 2026" → get_exchange_details(exchange_code="XETRA", start_date="2026-01-01", end_date="2026-03-31")
        """
        # --- Validate inputs ---
        exchange_code = sanitize_exchange(exchange_code)

        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        start_date = coerce_date_param(start_date, "start_date")
        end_date = coerce_date_param(end_date, "end_date")
        validate_date_range(start_date, end_date)

        # --- Build URL per docs ---
        url = build_url(
            f"exchange-details/{exchange_code}",
            {
                "fmt": fmt,
                "from": start_date,
                "to": end_date,
                "api_token": api_token,
            },
        )

        # --- Request ---
        data = await make_request(url)

        # --- Normalize response ---

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
