# app/tools/get_etf_holdings.py


import logging

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, sanitize_ticker
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="ETF Holdings", readOnlyHint=True))
    async def get_etf_holdings(
        ticker: str,  # US-listed ETF ticker, e.g. VTI or VTI.US (the .US suffix is optional)
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch the full list of positions held by a US-listed ETF, as the fund reported them in its
        SEC N-PORT filing. Use when the user asks what an ETF holds, its top holdings, position
        weights, sector or region breakdown, or asset allocation of a US ETF such as VTI, SPY or XLE.

        Beta API, US-listed ETFs only (other exchanges return 422). Not every US ETF is covered: some
        funds return 404. The positions come from the latest filing, so they can be several months
        old; data.General.Report_Date is the end of the filing period. Not paginated: all positions
        come back in one response, which is several MB for large funds (VTI has about 3,500
        positions, BND about 5 MB). Costs 10 API calls per request, a 404 included. Requires the
        Fundamentals Data Feed or All-In-One plan. The demo token works for VTI only.

        To find the ETFs that hold a given stock instead, use get_etf_held_by.

        Args:
            ticker (str): US ETF ticker, with or without the exchange suffix ("VTI" or "VTI.US").
            api_token (str, optional): Per-call token override.

        Returns:
            JSON envelope {data, meta, links}; meta and links are empty. data contains:
            - General (obj): Code, Type, Name, Exchange, Issuer, Fund_Type, Net_Assets (USD),
              Report_Date, Source ("nport"), Is_Complete (bool), Mapped_Weight_% (share of the
              fund weight whose positions have a ticker), Filed_Positions_Count
            - Holdings (obj): positions keyed by "CODE.EXCHANGE" (treat keys as opaque; a position
              without a ticker gets another key). Each: Code, Exchange, Name, Sector, Industry,
              Country, Country_Code, Region, Assets_% (weight in percent, can be negative),
              Shares, Value_USD, Contract_Code (set for options and other derivatives). For a fund
              with no positions Holdings is an empty list instead of an object.
            - Top_10_Holdings (obj): the ten largest positions, same shape as Holdings
            - Holdings_Count (int): number of entries in Holdings
            - Asset_Allocation (obj): Cash, Bond, Stock_US, Stock_non-US, Other; each with
              Long_%, Short_%, Net_Assets_%
            - Sector_Weights (obj): sector name -> {Equity_%}; equities only, empty for bond funds
            - World_Regions (obj): region name -> {Equity_%}; equities only
            - Performance (obj|null): Returns_YTD, Returns_1Y, Returns_3Y, Returns_5Y, Returns_10Y,
              1y_Volatility, 3y_Volatility, 3y_SharpRatio

        Notes:
            - 404 responses carry a code: FUND_NOT_FOUND (unknown ticker or renamed fund),
              NOT_COVERED (outside coverage, for example gold or bitcoin ETPs, ETNs, some small
              funds), NO_HOLDINGS_YET (known fund, no N-PORT filing yet).
            - 403 means the plan does not include this API.

        Examples:
            "What does VTI hold?" → get_etf_holdings(ticker="VTI")
            "Sector weights of XLE" → get_etf_holdings(ticker="XLE.US")
        """
        symbol = sanitize_ticker(ticker, param_name="ticker")

        url = build_url(f"etf/holdings/{symbol}", {"api_token": api_token})

        data = await make_request(url)

        return format_json_response(data)
