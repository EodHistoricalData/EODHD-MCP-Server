# app/tools/get_insider_summary.py
"""
Tool for fetching aggregated insider trading summary.
"""

import json
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_insider_summary(ticker: str) -> str:
        """
        Get aggregated insider trading summary for a stock.

        Args:
            ticker: Stock ticker with exchange (e.g., 'AAPL.US', 'NVDA.US')

        Returns:
            JSON with insider trading summary including:
            - Net shares purchased (sold)
            - Net transactions
            - Total buy/sell value
            - Insider sentiment indicators
        """
        if not ticker:
            return json.dumps({"error": "Parameter 'ticker' is required."}, indent=2)

        url = f"{EODHD_API_BASE}/fundamentals/{ticker}?filter=InsiderTransactions"
        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        return json.dumps(data, indent=2)
