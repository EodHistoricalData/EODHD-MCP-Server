# app/prompts/market_overview.py

from app.formatter import sanitize_prompt_param
from fastmcp import FastMCP


def register(mcp: FastMCP):
    @mcp.prompt
    def market_overview(exchange: str = "US") -> str:
        """
        Get a broad market overview using screener, economic events, and earnings data.

        Args:
            exchange: Exchange code (e.g. 'US', 'LSE', 'NSE'). Defaults to 'US'.
        """
        exchange = sanitize_prompt_param(exchange, "exchange")
        return (
            f"Provide a market overview for the {exchange} exchange.\n\n"
            f"Use these tools:\n"
            f"1. **get_stock_screener_data** — find top gainers and losers today "
            f"on {exchange} (sort by change_p descending, limit 10; "
            f"then sort ascending for losers, limit 10).\n"
            f"2. **get_economic_events** — upcoming economic events "
            f"for the next 7 days relevant to {exchange}.\n"
            f"3. **get_upcoming_earnings** — companies reporting earnings "
            f"in the next 7 days on {exchange}.\n\n"
            f"Summarize:\n"
            f"- **Market movers**: top 5 gainers and 5 losers with % change\n"
            f"- **Upcoming catalysts**: key economic events this week\n"
            f"- **Earnings watch**: notable companies reporting soon\n"
        )
