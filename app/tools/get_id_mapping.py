# app/tools/get_id_mapping.py
"""
Tool for ID mapping between different identifiers.
"""

import json
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_id_mapping(
        identifier: str,
        id_type: str = "auto"
    ) -> str:
        """
        Convert between different security identifiers (CUSIP, ISIN, FIGI, LEI, CIK, Symbol).

        Args:
            identifier: The identifier value to look up (e.g., 'US0378331005', '037833100')
            id_type: Type of identifier - 'cusip', 'isin', 'figi', 'lei', 'cik', 'auto' (default)
                     Use 'auto' to let the API detect the type automatically

        Returns:
            JSON with mapped identifiers including:
            - Symbol (ticker)
            - ISIN
            - CUSIP
            - FIGI
            - LEI
            - CIK
            - Exchange
        """
        if not identifier:
            return json.dumps({"error": "Parameter 'identifier' is required."}, indent=2)

        # Build URL based on id_type
        if id_type == "auto":
            # Try to detect type from format
            if len(identifier) == 12 and identifier[:2].isalpha():
                id_type = "isin"
            elif len(identifier) == 9 and identifier.isalnum():
                id_type = "cusip"
            elif len(identifier) == 12 and identifier.startswith("BBG"):
                id_type = "figi"
            elif len(identifier) == 20 and identifier.isalnum():
                id_type = "lei"
            elif identifier.isdigit():
                id_type = "cik"
            else:
                id_type = "isin"  # Default fallback

        url = f"{EODHD_API_BASE}/search-by-{id_type}/{identifier}?fmt=json"

        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        return json.dumps(data, indent=2)
