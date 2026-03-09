# app/prompts/analyze_stock.py

from fastmcp import FastMCP


def register(mcp: FastMCP):
    @mcp.prompt
    def analyze_stock(ticker: str) -> str:
        """
        Analyze a stock by chaining fundamental, technical, and news data.

        Args:
            ticker: Stock symbol in SYMBOL.EXCHANGE format (e.g. 'AAPL.US').
        """
        return (
            f"Perform a comprehensive analysis of {ticker}. "
            f"Use the following tools in order:\n\n"
            f"0. If '{ticker}' is a company name (not in SYMBOL.EXCHANGE format), "
            f"call **resolve_ticker** first to get the correct ticker symbol.\n"
            f"1. **get_fundamentals_data** for {ticker} — review valuation ratios, "
            f"financials, and balance sheet highlights.\n"
            f"2. **get_historical_stock_prices** for {ticker} over the last 6 months — "
            f"identify price trend, support/resistance levels, and momentum.\n"
            f"3. **get_technical_indicators** for {ticker} (SMA, RSI) — "
            f"confirm trend direction and overbought/oversold conditions.\n"
            f"4. **get_company_news** for {ticker} (last 30 days) — "
            f"summarize recent catalysts and sentiment.\n\n"
            f"Synthesize findings into:\n"
            f"- **Summary**: one-paragraph overview\n"
            f"- **Bull case**: key upside drivers\n"
            f"- **Bear case**: key risks\n"
            f"- **Key metrics table**: P/E, P/B, EPS, 52w range, RSI\n"
        )
