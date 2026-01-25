# app/tools/get_esg_data.py
"""
Tool for fetching ESG (Environmental, Social, Governance) data.
"""

import json
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_esg_data(ticker: str) -> str:
        """
        Get ESG (Environmental, Social, Governance) scores for a company.

        Args:
            ticker: Stock ticker with exchange (e.g., 'AAPL.US', 'MSFT.US')

        Returns:
            JSON with ESG scores including:
            - Total ESG score
            - Environmental score
            - Social score
            - Governance score
            - Controversy level
            - ESG activities and involvements
        """
        if not ticker:
            return json.dumps({"error": "Parameter 'ticker' is required."}, indent=2)

        url = f"{EODHD_API_BASE}/fundamentals/{ticker}?filter=ESGScores"
        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        return json.dumps(data, indent=2)
