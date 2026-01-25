# app/tools/get_analyst_ratings.py
"""
Tool for fetching analyst ratings and price targets.
"""

import json
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_analyst_ratings(ticker: str) -> str:
        """
        Get Wall Street analyst ratings and price targets for a stock.

        Args:
            ticker: Stock ticker with exchange (e.g., 'AAPL.US', 'TSLA.US')

        Returns:
            JSON with analyst ratings including:
            - Target price (high, low, mean, median)
            - Rating distribution (buy, sell, hold counts)
            - Individual analyst ratings history
        """
        if not ticker:
            return json.dumps({"error": "Parameter 'ticker' is required."}, indent=2)

        url = f"{EODHD_API_BASE}/fundamentals/{ticker}?filter=AnalystRatings"
        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        return json.dumps(data, indent=2)
