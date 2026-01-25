# app/tools/batch_quotes.py
"""
Tool for fetching batch quotes for multiple symbols.
"""

import json
import asyncio
from typing import List
from app.api_client import make_request
from app.config import EODHD_API_BASE


async def fetch_quote(ticker: str) -> dict:
    """Fetch a single quote."""
    url = f"{EODHD_API_BASE}/real-time/{ticker}?fmt=json"
    data = await make_request(url)
    return {"ticker": ticker, "data": data}


def register(mcp):
    @mcp.tool()
    async def get_batch_quotes(symbols: str) -> str:
        """
        Get quotes for multiple symbols at once.

        Args:
            symbols: Comma-separated list of tickers (e.g., 'AAPL.US,MSFT.US,GOOGL.US')

        Returns:
            JSON with quotes for all requested symbols
        """
        if not symbols:
            return json.dumps({"error": "Parameter 'symbols' is required."}, indent=2)

        # Parse symbols
        ticker_list = [s.strip() for s in symbols.split(",") if s.strip()]

        if not ticker_list:
            return json.dumps({"error": "No valid symbols provided."}, indent=2)

        if len(ticker_list) > 50:
            return json.dumps({"error": "Maximum 50 symbols allowed per request."}, indent=2)

        # Fetch all quotes concurrently
        tasks = [fetch_quote(ticker) for ticker in ticker_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Format results
        quotes = {}
        errors = []
        for result in results:
            if isinstance(result, Exception):
                errors.append(str(result))
            elif isinstance(result, dict):
                ticker = result.get("ticker")
                data = result.get("data")
                if data and not (isinstance(data, dict) and data.get("error")):
                    quotes[ticker] = data
                else:
                    errors.append(f"{ticker}: {data.get('error', 'Unknown error')}")

        response = {
            "quotes": quotes,
            "count": len(quotes),
            "requested": len(ticker_list)
        }
        if errors:
            response["errors"] = errors

        return json.dumps(response, indent=2)
