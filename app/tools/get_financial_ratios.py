# app/tools/get_financial_ratios.py
"""
Tool for fetching comprehensive financial ratios.
"""

import json
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_financial_ratios(ticker: str) -> str:
        """
        Get comprehensive financial ratios for a company.

        Args:
            ticker: Stock ticker with exchange (e.g., 'AAPL.US', 'MSFT.US')

        Returns:
            JSON with financial ratios including:
            - Valuation ratios (P/E, P/B, P/S, EV/EBITDA)
            - Profitability ratios (ROE, ROA, profit margins)
            - Liquidity ratios (current ratio, quick ratio)
            - Debt ratios (debt/equity, interest coverage)
            - Efficiency ratios (asset turnover, inventory turnover)
        """
        if not ticker:
            return json.dumps({"error": "Parameter 'ticker' is required."}, indent=2)

        url = f"{EODHD_API_BASE}/fundamentals/{ticker}?filter=Financials::Ratios"
        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        return json.dumps(data, indent=2)
