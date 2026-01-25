# app/tools/get_delisted_stocks.py
"""
Tool for fetching delisted stocks data.
"""

import json
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_delisted_stocks(exchange: str = "US") -> str:
        """
        Get list of delisted stocks for an exchange.

        Args:
            exchange: Exchange code (e.g., 'US', 'LSE'). Default is 'US'.

        Returns:
            JSON list of delisted stocks with:
            - Ticker symbol
            - Company name
            - Exchange
            - Delisting date
            - ISIN (if available)
        """
        if not exchange:
            return json.dumps({"error": "Parameter 'exchange' is required."}, indent=2)

        url = f"{EODHD_API_BASE}/exchange-symbol-list/{exchange}?type=delisted"
        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        return json.dumps(data, indent=2)
