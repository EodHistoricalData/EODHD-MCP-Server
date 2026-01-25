# app/tools/get_stock_peers.py
"""
Tool for finding similar companies/peers.
"""

import json
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_stock_peers(ticker: str, limit: int = 10) -> str:
        """
        Find similar companies (peers) for comparison.

        Args:
            ticker: Stock ticker with exchange (e.g., 'AAPL.US', 'MSFT.US')
            limit: Maximum number of peers to return (default: 10)

        Returns:
            JSON with peer companies including:
            - Ticker symbol
            - Company name
            - Market cap
            - Sector and industry
            - Key metrics for comparison
        """
        if not ticker:
            return json.dumps({"error": "Parameter 'ticker' is required."}, indent=2)

        # First get the company's sector/industry
        fundamentals_url = f"{EODHD_API_BASE}/fundamentals/{ticker}?filter=General"
        company_data = await make_request(fundamentals_url)

        if company_data is None or "error" in (company_data or {}):
            return json.dumps({"error": "Could not fetch company data."}, indent=2)

        sector = company_data.get("Sector", "")
        industry = company_data.get("Industry", "")
        exchange = ticker.split(".")[-1] if "." in ticker else "US"

        # Search for peers in same industry
        filters = [["exchange", "=", exchange]]
        if industry:
            filters.append(["industry", "=", industry])
        elif sector:
            filters.append(["sector", "=", sector])

        import urllib.parse
        filter_str = urllib.parse.quote(json.dumps(filters))
        screener_url = f"{EODHD_API_BASE}/screener?filters={filter_str}&sort=market_capitalization.desc&limit={limit + 1}"

        peers_data = await make_request(screener_url)

        if peers_data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        # Filter out the original ticker
        ticker_code = ticker.split(".")[0] if "." in ticker else ticker
        if isinstance(peers_data, dict) and "data" in peers_data:
            peers = [p for p in peers_data["data"] if p.get("code") != ticker_code][:limit]
            result = {
                "ticker": ticker,
                "sector": sector,
                "industry": industry,
                "peers": peers
            }
            return json.dumps(result, indent=2)

        return json.dumps(peers_data, indent=2)
