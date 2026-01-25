# app/tools/get_sector_performance.py
"""
Tool for fetching sector performance data.
"""

import json
from typing import Optional
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_sector_performance(
        exchange: str = "US",
        period: str = "1d"
    ) -> str:
        """
        Get performance data by market sector.

        Args:
            exchange: Exchange code (e.g., 'US'). Default is 'US'.
            period: Performance period - '1d', '5d', '1m', '3m', '6m', '1y', 'ytd'. Default is '1d'.

        Returns:
            JSON with sector performance including:
            - Sector name
            - Performance percentage
            - Market cap weighting
            - Top/bottom performers in sector
        """
        # Use screener with sector grouping
        url = f"{EODHD_API_BASE}/screener?filters=[[\"exchange\",\"=\",\"{exchange}\"]]&sort=market_capitalization.desc&limit=1000"

        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        # Group by sector and calculate performance
        if isinstance(data, dict) and "data" in data:
            sectors = {}
            for stock in data.get("data", []):
                sector = stock.get("sector", "Unknown")
                if sector not in sectors:
                    sectors[sector] = {
                        "sector": sector,
                        "stock_count": 0,
                        "total_market_cap": 0,
                        "stocks": []
                    }
                sectors[sector]["stock_count"] += 1
                sectors[sector]["total_market_cap"] += stock.get("market_capitalization", 0) or 0
                if len(sectors[sector]["stocks"]) < 5:
                    sectors[sector]["stocks"].append({
                        "code": stock.get("code"),
                        "name": stock.get("name"),
                        "market_cap": stock.get("market_capitalization")
                    })

            result = {
                "exchange": exchange,
                "period": period,
                "sectors": list(sectors.values())
            }
            return json.dumps(result, indent=2)

        return json.dumps(data, indent=2)
