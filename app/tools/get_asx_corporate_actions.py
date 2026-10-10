# app/tools/get_asx_corporate_actions.py

import logging

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, coerce_date_param, sanitize_ticker, validate_date_range
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)

# Action-type values accepted by the endpoint. Each groups one or more ASX
# ReferencePoint (E34) codes. Omit to return every action type.
ALLOWED_ACTION_TYPES = {
    "dividends",
    "splits",
    "bonus-issues",
    "rights-issues",
    "buybacks",
    "capital-returns",
    "spp",
    "other",
}
DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 1000


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="ASX Corporate Actions", readOnlyHint=True))
    async def get_asx_corporate_actions(
        action_type: str | None = None,  # maps to 'type' (dividends, splits, …)
        symbol: str | None = None,  # .AU ticker, maps to 'symbol' (e.g. "PMV.AU")
        start_date: str | None = None,  # maps to 'date_from' (YYYY-MM-DD, inclusive)
        end_date: str | None = None,  # maps to 'date_to'   (YYYY-MM-DD, inclusive)
        limit: int = DEFAULT_PAGE_LIMIT,  # maps to 'page[limit]' (1..1000)
        offset: int = 0,  # maps to 'page[offset]' (>= 0)
        fmt: str = "json",  # endpoint only supports json; tool gates to json
        api_token: str | None = None,  # per-call override; env token otherwise
    ) -> ResourceResponse:
        """

        Get structured corporate action data for ASX (Australian Securities Exchange) listed
        securities: dividends, splits, bonus issues, rights issues, buybacks, capital returns,
        and share purchase plans. Data is sourced from the official ASX ReferencePoint (E34)
        feed and refreshed daily. Coverage is limited to ASX-listed tickers (all use the .AU
        suffix). Costs 1 API call per request.

        Use when the user asks about Australian dividends and franking credits, ASX splits,
        bonus/rights issues, buybacks, capital returns, or share purchase plans. For corporate
        actions on other exchanges use get_historical_dividends / get_historical_splits.

        Args:
            action_type (str, optional): Corporate action category. One of: 'dividends',
                'splits', 'bonus-issues', 'rights-issues', 'buybacks', 'capital-returns',
                'spp', 'other'. Omit to return all types.
            symbol (str, optional): Ticker with .AU suffix (e.g. 'PMV.AU'). Filters to a
                single security.
            start_date (str, optional): 'date_from' in YYYY-MM-DD (inclusive, on event date).
            end_date (str, optional): 'date_to' in YYYY-MM-DD (inclusive, on event date).
            limit (int): Page size, 1..1000. Default 100.
            offset (int): Zero-based pagination offset. Default 0.
            fmt (str): 'json' only.
            api_token (str, optional): Per-call token override.

        Returns:
            Object with:
            - data (array): type-specific corporate-action records. Common fields include
              code, date, currency, exchange, recordDate, paymentDate/despatchDate. Dividend
              records add value/unadjustedValue/period plus an '_asx_extra' object carrying
              AU-specific fields (franked_amount_aud, franked_percent, drp_indicator,
              withholding_tax_rate, etc.). Splits add 'split', bonus/rights issues add 'ratio'.
            - meta (object): total (int) and page {offset, limit}.
            - links (object): next (str|null) — URL for the next page, null on the last page.

        Notes:
            - Pagination: when 'links.next' is not null, increment 'offset' (or follow that URL)
              to fetch the next page.
            - ASX only. Buybacks and 'other' categories are sparse — ASX publishes them less
              frequently than dividends or rights issues.
            - 1 API call per request.

        Examples:
            "Premier Investments ASX dividends" → symbol="PMV.AU", action_type="dividends"
            "All ASX splits in 2026" → action_type="splits", start_date="2026-01-01", end_date="2026-12-31"
            "Recent ASX corporate actions" → get_asx_corporate_actions()

        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        if fmt != "json":
            fmt = "json"

        if isinstance(action_type, str):
            action_type = action_type.strip().lower() or None

        if isinstance(symbol, str) and not symbol.strip():
            symbol = None
        elif symbol is not None:
            symbol = sanitize_ticker(symbol, param_name="symbol")

        start_date = coerce_date_param(start_date, "start_date")
        end_date = coerce_date_param(end_date, "end_date")
        validate_date_range(start_date, end_date)

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = DEFAULT_PAGE_LIMIT
        limit = max(1, min(limit, MAX_PAGE_LIMIT))

        try:
            offset = int(offset)
        except (TypeError, ValueError):
            offset = 0
        offset = max(0, offset)

        url = build_url(
            "asx-corporate-actions",
            {
                "type": action_type,
                "symbol": symbol,
                "date_from": start_date,
                "date_to": end_date,
                "page[limit]": limit,
                "page[offset]": offset,
                "fmt": fmt,
                "api_token": api_token,
            },
        )

        data = await make_request(url)

        return format_json_response(data)
