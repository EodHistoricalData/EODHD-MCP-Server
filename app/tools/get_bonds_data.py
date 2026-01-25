# app/tools/get_bonds_data.py
"""
Tool for fetching bond data.
"""

import json
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_bonds_data(identifier: str) -> str:
        """
        Get bond information by ISIN or CUSIP.

        Args:
            identifier: Bond ISIN or CUSIP (e.g., 'US912810RZ53')

        Returns:
            JSON with bond details including:
            - Bond name and issuer
            - Coupon rate
            - Maturity date
            - Yield to maturity
            - Credit rating
            - Price and yield history
        """
        if not identifier:
            return json.dumps({"error": "Parameter 'identifier' is required."}, indent=2)

        url = f"{EODHD_API_BASE}/bond-fundamentals/{identifier}"
        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        return json.dumps(data, indent=2)
