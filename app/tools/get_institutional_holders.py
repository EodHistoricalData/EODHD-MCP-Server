# app/tools/get_institutional_holders.py
"""
Tool for fetching institutional holders data.
"""

import json
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_institutional_holders(ticker: str) -> str:
        """
        Get major institutional investors/holders for a stock.

        Args:
            ticker: Stock ticker with exchange (e.g., 'AAPL.US', 'GOOGL.US')

        Returns:
            JSON with institutional holders including:
            - Institution name
            - Shares held
            - Percentage of shares outstanding
            - Change in holdings
            - Date reported
        """
        if not ticker:
            return json.dumps({"error": "Parameter 'ticker' is required."}, indent=2)

        url = f"{EODHD_API_BASE}/fundamentals/{ticker}?filter=Holders::Institutions"
        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        return json.dumps(data, indent=2)
