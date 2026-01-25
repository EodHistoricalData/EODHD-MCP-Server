# app/tools/get_historical_constituents.py
"""
Tool for fetching historical index constituents.
"""

import json
from typing import Optional
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_historical_constituents(
        index_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> str:
        """
        Get historical composition of major indices showing additions and deletions.

        Args:
            index_code: Index code (e.g., 'GSPC.INDX' for S&P 500, 'DJI.INDX' for Dow Jones)
            start_date: Optional start date in YYYY-MM-DD format
            end_date: Optional end date in YYYY-MM-DD format

        Returns:
            JSON with historical constituent changes including:
            - Date of change
            - Added symbols
            - Removed symbols
            - Reason for change
        """
        if not index_code:
            return json.dumps({"error": "Parameter 'index_code' is required."}, indent=2)

        url = f"{EODHD_API_BASE}/fundamentals/{index_code}?historical=1"

        if start_date:
            url += f"&from={start_date}"
        if end_date:
            url += f"&to={end_date}"

        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        return json.dumps(data, indent=2)
