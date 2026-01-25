# app/tools/get_forex_list.py
"""
Tool for fetching available forex pairs.
"""

import json
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_forex_list() -> str:
        """
        Get list of available forex currency pairs.

        Returns:
            JSON list of forex pairs with:
            - Symbol code (e.g., 'EURUSD', 'GBPUSD')
            - Currency names
            - Available data info
        """
        url = f"{EODHD_API_BASE}/exchange-symbol-list/FOREX"
        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        return json.dumps(data, indent=2)
