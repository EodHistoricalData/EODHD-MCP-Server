# app/tools/get_crypto_list.py
"""
Tool for fetching available cryptocurrencies.
"""

import json
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_crypto_list() -> str:
        """
        Get list of available cryptocurrencies.

        Returns:
            JSON list of crypto assets with:
            - Symbol code (e.g., 'BTC-USD', 'ETH-USD')
            - Crypto name
            - Quote currency
        """
        url = f"{EODHD_API_BASE}/exchange-symbol-list/CC"
        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        return json.dumps(data, indent=2)
