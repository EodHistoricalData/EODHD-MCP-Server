# get_upcoming_earnings.py

from app.api_client import make_request
from app.config import EODHD_API_BASE
from app.input_formatter import build_query_param
from app.response_formatter import ResourceResponse, format_json_response, format_text_response
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


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
    async def get_upcoming_earnings(
        start_date: str | None = None,  # maps to from= (YYYY-MM-DD)
        end_date: str | None = None,  # maps to to=   (YYYY-MM-DD)
        symbols: str | list[str] | None = None,  # 'AAPL.US' or ['AAPL.US','MSFT.US']
        fmt: str | None = "json",  # 'json' or 'csv' (docs default csv)
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Get upcoming and recent earnings report dates for stocks.
        Returns scheduled earnings dates, EPS estimates, and actual results when available.
        Filter by specific symbols or a date range (defaults to next 7 days).
        Use when the user asks "when does X report earnings?" or wants an earnings calendar.
        For EPS/revenue trend analysis and analyst revisions, use get_earnings_trends instead.
        For macroeconomic events (GDP, CPI), use get_economic_events instead.


        Returns:
            Object with:
            - earnings (list): array of earning records, each with:
              - code (str): ticker symbol
              - report_date (str): report filing date
              - date (str): earnings date
              - before_after_market (str|null): 'BeforeMarket' or 'AfterMarket'
              - currency (str): reporting currency
              - actual (float|null): actual EPS
              - estimate (float|null): consensus EPS estimate
              - difference (float|null): actual minus estimate
              - surprise_prc (float|null): surprise percentage

        Examples:
            "Apple earnings schedule" → symbols="AAPL.US"
            "Earnings this week" → start_date="2026-03-02", end_date="2026-03-06"
            "Microsoft and Google earnings" → symbols="MSFT.US,GOOG.US"


        Demo:
            To test data structure, use the test API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        sym_param = _normalize_symbols(symbols)

        # Build base URL
        url = f"{EODHD_API_BASE}/calendar/earnings?1=1"

        # Add parameters:
        if sym_param:
            url += build_query_param("symbols", sym_param)
            # Per spec: when symbols provided, 'from'/'to' are ignored — so we do NOT append them.
        else:
            url += build_query_param("from", start_date)
            url += build_query_param("to", end_date)

        url += build_query_param("fmt", (fmt or "json").lower())

        if api_token:
            url += build_query_param("api_token", api_token)  # otherwise appended by make_request via env

        # Hit API
        output_fmt = (fmt or "json").lower()
        data = await make_request(url, response_mode="text" if output_fmt == "csv" else "json")

        # Normalize output
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        if output_fmt == "csv":
            if not isinstance(data, str):
                raise ToolError("Unexpected CSV response format from API.")
            return format_text_response(data, "text/csv", resource_path="calendar/earnings.csv")

        return format_json_response(data)
