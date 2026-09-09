# app/tools/get_historical_commodity_prices.py

import logging

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, sanitize_ticker
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)

# Data frequencies the endpoint accepts. Not every commodity supports every
# interval (daily is energy-only; metals/agriculturals are typically monthly).
ALLOWED_INTERVALS = {"daily", "weekly", "monthly", "quarterly", "annual"}
DEFAULT_INTERVAL = "monthly"


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Historical Commodity Prices", readOnlyHint=True))
    async def get_historical_commodity_prices(
        code: str,  # commodity code, e.g. "WTI", "BRENT", "ALL_COMMODITIES"
        interval: str = DEFAULT_INTERVAL,  # daily|weekly|monthly|quarterly|annual
        api_token: str | None = None,  # per-call override; env token otherwise
    ) -> ResourceResponse:
        """

        Get historical price data for a commodity series (energy, metals, agriculturals, and
        commodity indices) sourced from FRED (Federal Reserve Economic Data). Series go back
        decades for major energy commodities. Costs 5 API calls per request.

        Use when the user asks for the price history of oil, gas, metals, or agricultural
        commodities, or a broad commodity index — e.g. WTI/Brent crude, natural gas, gasoline,
        diesel, copper, aluminum, wheat, corn, sugar, coffee, uranium, coal, or ALL_COMMODITIES.

        Available codes:
            Energy: WTI, BRENT, NATURAL_GAS, GASOLINE_US, DIESEL_USGULF, HEATING_OIL_NYH,
                JET_FUEL_USGULF, PROPANE_MBTX, COAL_AU, URANIUM
            Metals: ALUMINUM, COPPER
            Agricultural: WHEAT, CORN, SUGAR, COTTON, COFFEE_MILD_ARABICA, COFFEE_ROBUSTAS
            Indices: ALL_COMMODITIES, ALL_COMMODITIES_PRODUCER, ENERGY_INDEX, NATGAS_EU, LNG_ASIA

        Args:
            code (str): Commodity code (e.g. 'WTI', 'BRENT', 'URANIUM') or 'ALL_COMMODITIES'.
                Case-insensitive; normalized to upper case.
            interval (str): Data frequency — 'daily', 'weekly', 'monthly' (default),
                'quarterly', or 'annual'. Daily data is only available for energy commodities.
            api_token (str, optional): Per-call token override.

        Returns:
            Object with:
            - meta (object):
                - name (str): full commodity name from FRED
                - interval (str): data frequency
                - unit (str): measurement unit (e.g. 'Dollars per Barrel', 'Index 2016 = 100')
                - total (int): total number of data points available
            - data (array): records ordered newest-first, each with:
                - date (str): YYYY-MM-DD
                - value (float): price or index value

        Notes:
            - 5 API calls per request.
            - The 'demo' API key only returns WTI; other codes return 403 with that key.
            - Monthly metals/agriculturals/indices lag 2–3 weeks after month end; daily energy
              series are published by the EIA in weekly batches (up to ~1 week lag).

        Examples:
            "WTI crude oil price history" → code="WTI"
            "Daily Brent prices" → code="BRENT", interval="daily"
            "Annual copper prices" → code="COPPER", interval="annual"
            "Global all-commodities index" → code="ALL_COMMODITIES"

        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key only provides access to WTI in the Commodities API.
        """
        code = sanitize_ticker(code, param_name="code")
        if not code:
            return format_json_response(
                {"error": "Parameter 'code' is required (e.g., 'WTI', 'BRENT', 'ALL_COMMODITIES')."}
            )
        code = code.upper()

        if isinstance(interval, str):
            interval = interval.strip().lower()
        if interval not in ALLOWED_INTERVALS:
            interval = DEFAULT_INTERVAL

        url = build_url(
            f"commodities/historical/{code}",
            {
                "interval": interval,
                "api_token": api_token,
            },
        )

        data = await make_request(url)

        return format_json_response(data)
