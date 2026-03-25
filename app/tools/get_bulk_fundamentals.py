# app/tools/get_bulk_fundamentals.py

import logging
from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, sanitize_exchange
from app.response_formatter import ResourceResponse, format_json_response, format_text_response, raise_on_api_error

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_bulk_fundamentals(
        exchange: str,  # e.g. "NASDAQ", "NYSE", "US", "LSE"
        symbols: str | None = None,  # comma-separated list, e.g. "AAPL,MSFT,GOOG"
        offset: int | str | None = None,  # pagination start (default 0)
        limit: int | str | None = None,  # max symbols (default 500, max 500)
        version: str | None = None,  # "1.2" for single-symbol-like output
        fmt: str = "json",  # 'json' (default) or 'csv'
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch fundamental data for all stocks on an exchange in bulk. Use when the user needs
        financials, valuation, or earnings data for many companies at once -- screening,
        comparing sectors, or building dashboards across an entire exchange.

        Returns General, Highlights, Valuation, Technicals, SplitsDividends, Earnings (last 4
        quarters + 4 years), and Financials for up to 500 stocks per call. Stocks only (no ETFs
        or mutual funds). Costs 100 API calls per request. Requires Extended Fundamentals plan.

        For a single ticker's full fundamentals, use get_fundamentals_data instead.
        For macro country-level economic data, use get_macro_indicator.

        Args:
            exchange (str): Exchange code (e.g., 'NASDAQ', 'NYSE', 'US', 'LSE').
            symbols (str, optional): Comma-separated list of specific symbols to filter.
            offset (int, optional): Pagination start (default 0).
            limit (int, optional): Max symbols to return (default 500, max 500).
            version (str, optional): '1.2' for single-symbol-like output format.
            fmt (str): 'json' (default) or 'csv'.
            api_token (str, optional): Per-call token override.


        Returns:
            Dict of ticker -> fundamentals object, each with:
            - General (object): Code, Type, Name, Exchange, CurrencyCode, CurrencyName, CountryName, ISIN, Sector, Industry
            - Highlights (object): MarketCapitalization, EBITDA, PERatio, WallStreetTargetPrice, BookValue, EarningsShare, DividendYield
            - Valuation (object): TrailingPE, ForwardPE, PriceSalesTTM, PriceBookMRQ, EnterpriseValue
            - SharesStats (object): SharesOutstanding, SharesFloat, PercentInsiders, PercentInstitutions
            - Technicals (object): Beta, 52WeekHigh, 52WeekLow, 50DayMA, 200DayMA
            - SplitsDividends (object): ForwardAnnualDividendRate, ForwardAnnualDividendYield, ExDividendDate, LastSplitDate, LastSplitFactor
            - Earnings (object): Last_4_Quarters (array), Annual_Earnings (array)
            - Financials (object): Income_Statement, Balance_Sheet, Cash_Flow (quarterly + yearly)

        Notes:
            - Requires Extended Fundamentals subscription plan.
            - API cost: 100 calls per request (or 100 + number of symbols if using symbols param).
            - Stocks only (no ETFs or Mutual Funds).
            - Max pagination limit: 500.
            - Historical data limited to 4 quarters and 4 years.

        Examples:
            "Fundamentals for all NASDAQ stocks" → get_bulk_fundamentals(exchange="NASDAQ")
            "AAPL and MSFT fundamentals from NYSE" → get_bulk_fundamentals(exchange="US", symbols="AAPL,MSFT")
            "LSE fundamentals, second page" → get_bulk_fundamentals(exchange="LSE", offset=500, limit=500)


        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        exchange = sanitize_exchange(exchange, param_name="exchange").upper()

        allowed_fmt = {"json", "csv"}
        fmt = (fmt or "json").lower()
        if fmt not in allowed_fmt:
            raise ToolError(f"Invalid 'fmt'. Allowed: {sorted(allowed_fmt)}")

        off = None
        if offset is not None:
            try:
                off = int(offset)
            except (ValueError, TypeError):
                raise ToolError("Parameter 'offset' must be a non-negative integer.")
            if off < 0:
                raise ToolError("Parameter 'offset' must be a non-negative integer.")

        lim = None
        if limit is not None:
            try:
                lim = int(limit)
            except (ValueError, TypeError):
                raise ToolError("Parameter 'limit' must be a positive integer (max 500).")
            if lim <= 0 or lim > 500:
                raise ToolError("Parameter 'limit' must be between 1 and 500.")

        url = build_url(
            f"bulk-fundamentals/{quote_plus(exchange)}",
            {
                "fmt": fmt,
                "symbols": symbols.strip() if symbols else None,
                "offset": off,
                "limit": lim,
                "version": version.strip() if version else None,
                "api_token": api_token,
            },
        )

        data = await make_request(url, response_mode="text" if fmt == "csv" else "json")
        raise_on_api_error(data)

        if fmt == "csv":
            if not isinstance(data, str):
                raise ToolError("Unexpected CSV response format from API.")
            return format_text_response(data, "text/csv", resource_path=f"bulk-fundamentals/{quote_plus(exchange)}.csv")

        return format_json_response(data)
