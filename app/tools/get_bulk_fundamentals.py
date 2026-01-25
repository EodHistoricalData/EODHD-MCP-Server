# app/tools/get_bulk_fundamentals.py
"""
Tool for fetching bulk fundamentals data.
"""

import json
from typing import Optional
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_bulk_fundamentals(
        exchange: str,
        symbols: Optional[str] = None,
        offset: int = 0,
        limit: int = 500
    ) -> str:
        """
        Get bulk fundamentals data for multiple symbols on an exchange.

        Args:
            exchange: Exchange code (e.g., 'US', 'LSE')
            symbols: Optional comma-separated list of symbols to filter
            offset: Pagination offset (default: 0)
            limit: Number of results to return (default: 500, max: 1000)

        Returns:
            JSON with fundamentals data for multiple symbols
        """
        if not exchange:
            return json.dumps({"error": "Parameter 'exchange' is required."}, indent=2)

        url = f"{EODHD_API_BASE}/bulk-fundamentals/{exchange}?offset={offset}&limit={limit}"

        if symbols:
            url += f"&symbols={symbols}"

        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        return json.dumps(data, indent=2)
