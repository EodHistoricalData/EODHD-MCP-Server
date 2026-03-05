# app/prompts/compare_stocks.py

from fastmcp import FastMCP


def register(mcp: FastMCP):
    @mcp.prompt
    def compare_stocks(ticker1: str, ticker2: str) -> str:
        """
        Compare two stocks side by side using fundamental and price data.

        Args:
            ticker1: First stock symbol in SYMBOL.EXCHANGE format (e.g. 'AAPL.US').
            ticker2: Second stock symbol in SYMBOL.EXCHANGE format (e.g. 'MSFT.US').
        """
        return (
            f"Compare {ticker1} and {ticker2} side by side.\n\n"
            f"For each stock, fetch:\n"
            f"1. **get_fundamentals_data** — valuation, profitability, growth metrics.\n"
            f"2. **get_historical_stock_prices** (last 12 months) — price performance.\n"
            f"3. **get_live_price_data** — current price and change.\n\n"
            f"Present a comparison table with:\n"
            f"| Metric | {ticker1} | {ticker2} |\n"
            f"|--------|-----------|----------|\n"
            f"| Market Cap | | |\n"
            f"| P/E Ratio | | |\n"
            f"| Revenue Growth | | |\n"
            f"| Profit Margin | | |\n"
            f"| 52-Week Return | | |\n"
            f"| Dividend Yield | | |\n\n"
            f"End with a brief verdict: which stock looks stronger and why."
        )
