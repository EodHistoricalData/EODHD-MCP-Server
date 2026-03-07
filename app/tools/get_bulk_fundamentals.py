# get_bulk_fundamentals.py

import json
from urllib.parse import quote_plus

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def _q(key: str, val: str | int | None) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


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
    ) -> str:
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

        
        """
        if not exchange or not isinstance(exchange, str):
            raise ToolError(
                "Parameter 'exchange' is required and must be a non-empty string (e.g., 'NASDAQ', 'NYSE', 'US')."
            )

        exchange = exchange.strip().upper()

        allowed_fmt = {"json", "csv"}
        fmt = (fmt or "json").lower()
        if fmt not in allowed_fmt:
            raise ToolError(f"Invalid 'fmt'. Allowed: {sorted(allowed_fmt)}")

        url = f"{EODHD_API_BASE}/bulk-fundamentals/{quote_plus(exchange)}?fmt={fmt}"

        if symbols:
            url += _q("symbols", symbols.strip())

        if offset is not None:
            try:
                off = int(offset)
            except (ValueError, TypeError):
                raise ToolError("Parameter 'offset' must be a non-negative integer.")
            if off < 0:
                raise ToolError("Parameter 'offset' must be a non-negative integer.")
            url += f"&offset={off}"

        if limit is not None:
            try:
                lim = int(limit)
            except (ValueError, TypeError):
                raise ToolError("Parameter 'limit' must be a positive integer (max 500).")
            if lim <= 0 or lim > 500:
                raise ToolError("Parameter 'limit' must be between 1 and 500.")
            url += f"&limit={lim}"

        if version:
            url += _q("version", version.strip())

        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return json.dumps(data, indent=2)
        except Exception:
            if isinstance(data, str):
                return json.dumps({"csv": data}, indent=2)
            raise ToolError("Unexpected response format from API.")
