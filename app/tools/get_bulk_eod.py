# app/tools/get_bulk_eod.py
"""
Tool for fetching bulk EOD data for entire exchanges.
"""

import json
from typing import Optional
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_bulk_eod(
        exchange: str,
        date: Optional[str] = None,
        data_type: str = "eod",
        symbols: Optional[str] = None
    ) -> str:
        """
        Get bulk end-of-day data for all tickers on an exchange.

        Args:
            exchange: Exchange code (e.g., 'US', 'LSE', 'NSE')
            date: Optional date in YYYY-MM-DD format (default: latest)
            data_type: Type of data - 'eod' (default), 'splits', or 'dividends'
            symbols: Optional comma-separated list of symbols to filter

        Returns:
            JSON with bulk data for all (or filtered) symbols on the exchange
        """
        if not exchange:
            return json.dumps({"error": "Parameter 'exchange' is required."}, indent=2)

        url = f"{EODHD_API_BASE}/eod-bulk-last-day/{exchange}?fmt=json"

        if date:
            url += f"&date={date}"
        if data_type and data_type != "eod":
            url += f"&type={data_type}"
        if symbols:
            url += f"&symbols={symbols}"

        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        return json.dumps(data, indent=2)
