# get_exchanges_list.py

import json

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_exchanges_list(
        fmt: str = "json",  # API supports csv too; tool defaults to json
        api_token: str | None = None,  # per-call override (env token otherwise)
    ) -> str:
        """

        List all available stock exchanges worldwide. Use when the user asks which exchanges
        are supported, needs exchange codes, or wants to browse markets by country.

        Covers 60+ global exchanges. Returns Name, Code, OperatingMIC, Country, Currency,
        and ISO country codes for each exchange.

        For tickers listed on a specific exchange, use get_exchange_tickers.
        For trading hours, holidays, and metadata of one exchange, use get_exchange_details.


        Returns:
            Array of exchange objects, each with:
            - Name (str): exchange full name
            - Code (str): exchange code (e.g. "US", "LSE")
            - OperatingMIC (str): ISO 10383 operating MIC
            - Country (str): country name
            - Currency (str): primary currency code
            - CountryISO2 (str): ISO 3166-1 alpha-2 country code
            - CountryISO3 (str): ISO 3166-1 alpha-3 country code

        Examples:
            "List all available exchanges" → get_exchanges_list()
            "What stock exchanges does EODHD support?" → get_exchanges_list()


        """
        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        url = f"{EODHD_API_BASE}/exchanges-list/?fmt={fmt}"
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
            raise ToolError("Unexpected response format from API.")
