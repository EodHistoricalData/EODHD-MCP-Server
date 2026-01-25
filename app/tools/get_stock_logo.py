# app/tools/get_stock_logo.py
"""
Tool for fetching company logo URLs.
"""

import json
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_stock_logo(ticker: str) -> str:
        """
        Get company logo URL for a stock.

        Args:
            ticker: Stock ticker with exchange (e.g., 'AAPL.US', 'MSFT.US')

        Returns:
            JSON with logo URL and company info
        """
        if not ticker:
            return json.dumps({"error": "Parameter 'ticker' is required."}, indent=2)

        url = f"{EODHD_API_BASE}/fundamentals/{ticker}?filter=General::LogoURL,General::Name,General::Code"
        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        return json.dumps(data, indent=2)
