# get_macro_indicator.py

import json
import re

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

ISO3_RE = re.compile(r"^[A-Z]{3}$")
ALLOWED_FMT = {"json", "csv"}

# From documentation (canonical list)
ALLOWED_INDICATORS = {
    "real_interest_rate",
    "population_total",
    "population_growth_annual",
    "inflation_consumer_prices_annual",
    "consumer_price_index",
    "gdp_current_usd",
    "gdp_per_capita_usd",
    "gdp_growth_annual",
    "debt_percent_gdp",
    "net_trades_goods_services",
    "inflation_gdp_deflator_annual",
    "agriculture_value_added_percent_gdp",
    "industry_value_added_percent_gdp",
    "services_value_added_percent_gdp",
    "exports_of_goods_services_percent_gdp",
    "imports_of_goods_services_percent_gdp",
    "gross_capital_formation_percent_gdp",
    "net_migration",
    "gni_usd",
    "gni_per_capita_usd",
    "gni_ppp_usd",
    "gni_per_capita_ppp_usd",
    "income_share_lowest_twenty",
    "life_expectancy",
    "fertility_rate",
    "prevalence_hiv_total",
    "co2_emissions_tons_per_capita",
    "surface_area_km",
    "poverty_poverty_lines_percent_population",
    "revenue_excluding_grants_percent_gdp",
    "cash_surplus_deficit_percent_gdp",
    "startup_procedures_register",
    "market_cap_domestic_companies_percent_gdp",
    "mobile_subscriptions_per_hundred",
    "internet_users_per_hundred",
    "high_technology_exports_percent_total",
    "merchandise_trade_percent_gdp",
    "total_debt_service_percent_gni",
    "unemployment_total_percent",
}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_macro_indicator(
        country: str,  # ISO-3, e.g., USA, FRA, DEU
        indicator: str | None = None,  # default: gdp_current_usd
        fmt: str = "json",  # 'json' or 'csv' (API default json here)
        api_token: str | None = None,  # per-call override; env otherwise
    ) -> str:
        """

        Fetch macroeconomic indicators for a country over time. Use when the user asks about
        country-level economic data: GDP, inflation, CPI, unemployment, population, trade
        balance, debt-to-GDP, life expectancy, and 30+ other World Bank-style indicators.

        Returns a historical time series for one indicator in one country. Country is specified
        by ISO-3 alpha code (e.g., USA, DEU, FRA). Defaults to GDP if no indicator specified.

        This is for country-level macro data only. For company fundamentals, use
        get_fundamentals_data (single ticker) or get_bulk_fundamentals (entire exchange).

        Args:
            country (str): Alpha-3 ISO country code (e.g., 'USA', 'FRA', 'DEU').
            indicator (str, optional): One of documented indicators. Defaults to 'gdp_current_usd'.
            fmt (str): 'json' or 'csv'. Default 'json'.
            api_token (str, optional): Per-call token override.


        Returns:
            Array of indicator data points, each with:
            - CountryCode (str): ISO-3 country code (e.g. "USA")
            - Indicator (str): indicator key (e.g. "gdp_current_usd")
            - Date (str): observation date (YYYY-MM-DD)
            - Period (str): reporting period
            - Value (float): indicator value
            - Frequency (str): data frequency (e.g. "Annual")
            - Unit (str): measurement unit

        Examples:
            "US GDP over time" → get_macro_indicator(country="USA", indicator="gdp_current_usd")
            "Germany unemployment rate" → get_macro_indicator(country="DEU", indicator="unemployment_total_percent")
            "France inflation (CPI)" → get_macro_indicator(country="FRA", indicator="inflation_consumer_prices_annual")


        """
        # --- Validate inputs ---
        if not country or not isinstance(country, str) or not ISO3_RE.match(country.upper()):
            raise ToolError("Parameter 'country' must be an Alpha-3 ISO code (e.g., 'USA', 'FRA', 'DEU').")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        use_indicator = indicator or "gdp_current_usd"
        if use_indicator not in ALLOWED_INDICATORS:
            raise ToolError(
                "Invalid 'indicator'. Provide one of the documented indicators or omit it to use 'gdp_current_usd'."
            )

        # --- Build URL ---
        # Example: /api/macro-indicator/USA?indicator=inflation_consumer_prices_annual&fmt=json
        url = f"{EODHD_API_BASE}/macro-indicator/{country.upper()}?indicator={use_indicator}&fmt={fmt}"
        if api_token:
            url += f"&api_token={api_token}"  # otherwise make_request appends env token

        # --- Request ---
        data = await make_request(url)

        # --- Normalize / return ---
        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        # If fmt=json, API returns JSON -> dump.
        # If you adapt make_request to return text for fmt='csv', we'll wrap it.
        try:
            return json.dumps(data, indent=2)
        except Exception:
            if isinstance(data, str):
                return json.dumps({"csv": data}, indent=2)
            raise ToolError("Unexpected response format from API.")
