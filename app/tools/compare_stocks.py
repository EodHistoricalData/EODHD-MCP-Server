# app/tools/compare_stocks.py
"""
Tool for side-by-side stock comparison.
"""

import json
import asyncio
from app.api_client import make_request
from app.config import EODHD_API_BASE


async def fetch_fundamentals(ticker: str) -> dict:
    """Fetch fundamentals for a single ticker."""
    url = f"{EODHD_API_BASE}/fundamentals/{ticker}?filter=General,Highlights,Valuation"
    data = await make_request(url)
    return {"ticker": ticker, "data": data}


def register(mcp):
    @mcp.tool()
    async def compare_stocks(symbols: str) -> str:
        """
        Side-by-side comparison of multiple stocks.

        Args:
            symbols: Comma-separated list of tickers to compare (e.g., 'AAPL.US,MSFT.US,GOOGL.US')

        Returns:
            JSON with comparison data including:
            - Company info
            - Market cap
            - P/E ratio
            - Revenue
            - Profit margins
            - Growth metrics
        """
        if not symbols:
            return json.dumps({"error": "Parameter 'symbols' is required."}, indent=2)

        # Parse symbols
        ticker_list = [s.strip() for s in symbols.split(",") if s.strip()]

        if len(ticker_list) < 2:
            return json.dumps({"error": "At least 2 symbols required for comparison."}, indent=2)

        if len(ticker_list) > 10:
            return json.dumps({"error": "Maximum 10 symbols allowed for comparison."}, indent=2)

        # Fetch all fundamentals concurrently
        tasks = [fetch_fundamentals(ticker) for ticker in ticker_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build comparison table
        comparison = []
        for result in results:
            if isinstance(result, Exception):
                continue
            if not isinstance(result, dict):
                continue

            ticker = result.get("ticker")
            data = result.get("data", {})

            if not data or (isinstance(data, dict) and data.get("error")):
                continue

            general = data.get("General", {})
            highlights = data.get("Highlights", {})
            valuation = data.get("Valuation", {})

            comparison.append({
                "ticker": ticker,
                "name": general.get("Name"),
                "sector": general.get("Sector"),
                "industry": general.get("Industry"),
                "market_cap": highlights.get("MarketCapitalization"),
                "pe_ratio": highlights.get("PERatio"),
                "peg_ratio": highlights.get("PEGRatio"),
                "eps": highlights.get("EarningsShare"),
                "dividend_yield": highlights.get("DividendYield"),
                "profit_margin": highlights.get("ProfitMargin"),
                "roe": highlights.get("ReturnOnEquityTTM"),
                "revenue": highlights.get("RevenueTTM"),
                "revenue_growth": highlights.get("QuarterlyRevenueGrowthYOY"),
                "target_price": highlights.get("WallStreetTargetPrice"),
                "forward_pe": valuation.get("ForwardPE"),
                "price_to_book": valuation.get("PriceBookMRQ"),
                "ev_ebitda": valuation.get("EnterpriseValueEbitda")
            })

        if not comparison:
            return json.dumps({"error": "Could not fetch data for any symbols."}, indent=2)

        response = {
            "comparison": comparison,
            "count": len(comparison),
            "metrics": [
                "market_cap", "pe_ratio", "peg_ratio", "eps", "dividend_yield",
                "profit_margin", "roe", "revenue", "revenue_growth", "target_price",
                "forward_pe", "price_to_book", "ev_ebitda"
            ]
        }

        return json.dumps(response, indent=2)
