# app/tools/get_short_interest.py
"""
Tool for fetching short interest data.
"""

import json
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_short_interest(ticker: str) -> str:
        """
        Get short interest data and metrics for a stock.

        Args:
            ticker: Stock ticker with exchange (e.g., 'GME.US', 'AMC.US')

        Returns:
            JSON with short interest data including:
            - Short interest (shares shorted)
            - Short percent of float
            - Days to cover
            - Short interest ratio
            - Historical short interest data
        """
        if not ticker:
            return json.dumps({"error": "Parameter 'ticker' is required."}, indent=2)

        url = f"{EODHD_API_BASE}/fundamentals/{ticker}?filter=SharesStats"
        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        return json.dumps(data, indent=2)
