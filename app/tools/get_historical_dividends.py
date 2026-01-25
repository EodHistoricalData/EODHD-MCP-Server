# app/tools/get_historical_dividends.py
"""
Tool for fetching complete dividend history.
"""

import json
from typing import Optional
from app.api_client import make_request
from app.config import EODHD_API_BASE


def register(mcp):
    @mcp.tool()
    async def get_historical_dividends(
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> str:
        """
        Get complete dividend history with analytics.

        Args:
            ticker: Stock ticker with exchange (e.g., 'AAPL.US', 'JNJ.US')
            start_date: Optional start date in YYYY-MM-DD format
            end_date: Optional end date in YYYY-MM-DD format

        Returns:
            JSON with dividend history including:
            - Historical dividend payments
            - Ex-dividend dates
            - Payment dates
            - Dividend yield over time
            - Dividend growth rate
        """
        if not ticker:
            return json.dumps({"error": "Parameter 'ticker' is required."}, indent=2)

        url = f"{EODHD_API_BASE}/div/{ticker}?fmt=json"

        if start_date:
            url += f"&from={start_date}"
        if end_date:
            url += f"&to={end_date}"

        data = await make_request(url)

        if data is None:
            return json.dumps({"error": "No response from API."}, indent=2)

        # Add analytics if we have data
        if isinstance(data, list) and len(data) > 1:
            # Calculate dividend growth
            dividends = sorted(data, key=lambda x: x.get("date", ""))
            total_dividends = sum(d.get("value", 0) for d in dividends if d.get("value"))

            # Year-over-year growth (simplified)
            years = {}
            for d in dividends:
                year = d.get("date", "")[:4]
                if year:
                    years[year] = years.get(year, 0) + (d.get("value", 0) or 0)

            result = {
                "ticker": ticker,
                "dividend_history": data,
                "analytics": {
                    "total_payments": len(dividends),
                    "total_dividends": round(total_dividends, 4),
                    "annual_totals": years
                }
            }
            return json.dumps(result, indent=2)

        return json.dumps(data, indent=2)
