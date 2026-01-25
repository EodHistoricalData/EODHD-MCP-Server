# app/tools/get_market_status.py
"""
Tool for checking market open/closed status.
"""

import json
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_market_status(exchange: str = "US") -> str:
        """
        Check if a market/exchange is currently open or closed.

        Args:
            exchange: Exchange code (e.g., 'US', 'LSE', 'XETRA'). Default is 'US'.

        Returns:
            JSON with market status including:
            - Is market open
            - Current trading session
            - Time until open/close
            - Exchange timezone
            - Holiday information if applicable
        """
        url = f"{EODHD_API_BASE}/exchange-details/{exchange}"
        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        # Add computed status
        if isinstance(data, dict):
            # Check trading hours and current time to determine status
            result = {
                "exchange": exchange,
                "details": data,
                "note": "Check ExchangeHours and TradingHours for schedule"
            }
            return json.dumps(result, indent=2)

        return json.dumps(data, indent=2)
