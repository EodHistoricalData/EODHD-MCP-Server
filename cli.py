#!/usr/bin/env python3
# cli.py
"""
Command-line utilities for EODHD MCP Server.
"""

import argparse
import asyncio
import json
import sys

from app.config import EODHD_API_KEY, EODHD_API_BASE
from app.api_client import make_request


async def check_api_key():
    """Validate the API key."""
    print(f"API Base: {EODHD_API_BASE}")
    print(f"API Key: {'*' * (len(EODHD_API_KEY) - 4) + EODHD_API_KEY[-4:] if len(EODHD_API_KEY) > 4 else '****'}")

    url = f"{EODHD_API_BASE}/user?fmt=json"
    result = await make_request(url)

    if result and not result.get("error"):
        print("\nAPI Key Status: VALID")
        print(f"API Calls Today: {result.get('apiRequests', 'N/A')}")
        print(f"Daily Limit: {result.get('dailyRateLimit', 'N/A')}")
        return True
    else:
        print(f"\nAPI Key Status: INVALID")
        print(f"Error: {result.get('error', 'Unknown error')}")
        return False


async def get_quote(ticker: str):
    """Get a real-time quote for a ticker."""
    url = f"{EODHD_API_BASE}/real-time/{ticker}?fmt=json"
    result = await make_request(url)

    if result and not result.get("error"):
        print(f"\n{ticker} Quote:")
        print(f"  Price: {result.get('close', 'N/A')}")
        print(f"  Open:  {result.get('open', 'N/A')}")
        print(f"  High:  {result.get('high', 'N/A')}")
        print(f"  Low:   {result.get('low', 'N/A')}")
        print(f"  Volume: {result.get('volume', 'N/A')}")
        print(f"  Change: {result.get('change', 'N/A')} ({result.get('change_p', 'N/A')}%)")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")


async def search_stocks(query: str):
    """Search for stocks by name or symbol."""
    url = f"{EODHD_API_BASE}/search/{query}?fmt=json"
    result = await make_request(url)

    if result and not isinstance(result, dict):
        print(f"\nSearch results for '{query}':")
        for item in result[:10]:
            print(f"  {item.get('Code', 'N/A')}.{item.get('Exchange', '')} - {item.get('Name', 'N/A')}")
    elif result and result.get("error"):
        print(f"Error: {result.get('error')}")
    else:
        print("No results found.")


async def get_history(ticker: str, limit: int = 10):
    """Get historical prices for a ticker."""
    url = f"{EODHD_API_BASE}/eod/{ticker}?fmt=json&order=d&limit={limit}"
    result = await make_request(url)

    if result and not isinstance(result, dict):
        print(f"\n{ticker} Price History (last {limit} days):")
        print(f"{'Date':<12} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10} {'Volume':>12}")
        print("-" * 70)
        for row in result:
            print(f"{row.get('date', 'N/A'):<12} {row.get('open', 0):>10.2f} {row.get('high', 0):>10.2f} {row.get('low', 0):>10.2f} {row.get('close', 0):>10.2f} {row.get('volume', 0):>12}")
    elif result and result.get("error"):
        print(f"Error: {result.get('error')}")


async def list_exchanges():
    """List all available exchanges."""
    url = f"{EODHD_API_BASE}/exchanges-list/?fmt=json"
    result = await make_request(url)

    if result and not isinstance(result, dict):
        print("\nAvailable Exchanges:")
        for ex in result:
            print(f"  {ex.get('Code', 'N/A'):>6} - {ex.get('Name', 'N/A')} ({ex.get('Country', 'N/A')})")
    elif result and result.get("error"):
        print(f"Error: {result.get('error')}")


def list_tools():
    """List all available MCP tools."""
    from app.tools import ALL_TOOLS
    print(f"\nAvailable Tools ({len(ALL_TOOLS)} total):")
    for i, tool in enumerate(ALL_TOOLS, 1):
        print(f"  {i:2}. {tool}")


def main():
    parser = argparse.ArgumentParser(
        description="EODHD MCP Server CLI Utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py check              # Validate API key
  python cli.py quote AAPL.US      # Get stock quote
  python cli.py search microsoft   # Search for stocks
  python cli.py history TSLA.US    # Get price history
  python cli.py exchanges          # List exchanges
  python cli.py tools              # List MCP tools
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # check command
    subparsers.add_parser("check", help="Validate API key")

    # quote command
    quote_parser = subparsers.add_parser("quote", help="Get stock quote")
    quote_parser.add_argument("ticker", help="Stock ticker (e.g., AAPL.US)")

    # search command
    search_parser = subparsers.add_parser("search", help="Search for stocks")
    search_parser.add_argument("query", help="Search query")

    # history command
    history_parser = subparsers.add_parser("history", help="Get price history")
    history_parser.add_argument("ticker", help="Stock ticker (e.g., AAPL.US)")
    history_parser.add_argument("-n", "--limit", type=int, default=10, help="Number of days")

    # exchanges command
    subparsers.add_parser("exchanges", help="List exchanges")

    # tools command
    subparsers.add_parser("tools", help="List MCP tools")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "check":
        asyncio.run(check_api_key())
    elif args.command == "quote":
        asyncio.run(get_quote(args.ticker))
    elif args.command == "search":
        asyncio.run(search_stocks(args.query))
    elif args.command == "history":
        asyncio.run(get_history(args.ticker, args.limit))
    elif args.command == "exchanges":
        asyncio.run(list_exchanges())
    elif args.command == "tools":
        list_tools()


if __name__ == "__main__":
    main()
