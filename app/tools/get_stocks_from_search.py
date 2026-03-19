# get_stocks_from_search.py

from urllib.parse import quote

from app.api_client import make_request
from app.config import EODHD_API_BASE
from app.response import format_json_response
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

ALLOWED_TYPES = {"all", "stock", "etf", "fund", "bond", "index", "crypto"}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_stocks_from_search(
        query: str,
        limit: int = 15,  # per docs: default 15, max 500
        bonds_only: bool | None = None,  # maps to bonds_only=1
        exchange: str | None = None,  # e.g., "US", "PA", "FOREX", "NYSE", "NASDAQ"
        type: str | None = None,  # one of ALLOWED_TYPES
        fmt: str = "json",  # API supports json here
        api_token: str | None = None,  # per-call override
    ) -> list:
        """

        Search for financial instruments by name, ticker, or ISIN. Use when the user wants to
        find a ticker symbol, look up a company by name, resolve an ISIN, or discover instruments
        matching a keyword.

        Searches across stocks, ETFs, mutual funds, bonds, indices, and crypto. Returns matching
        instruments with their ticker codes, exchange, type, and ISIN. Filterable by exchange
        and instrument type.

        This is the discovery/lookup tool. Once you have a ticker, use other tools (e.g.,
        get_eod_historical_data, get_fundamentals_data) to fetch actual data.

        Args:
            query (str): Ticker, company name, or ISIN to search (e.g., 'AAPL', 'Apple Inc', 'US0378331005').
            limit (int): Number of results (default 15, max 500).
            bonds_only (bool, optional): If True, return only bonds.
            exchange (str, optional): Exchange code filter (e.g., 'US', 'PA', 'FOREX', 'NYSE').
            type (str, optional): One of {'all','stock','etf','fund','bond','index','crypto'}.
            fmt (str): Must be 'json'.
            api_token (str, optional): Per-call API token override (demo token does NOT work for Search).


        Returns:
            Array of matching instruments, each with:
            - Code (str): ticker symbol
            - Exchange (str): exchange code
            - Name (str): instrument name
            - Type (str): instrument type (e.g. "Common Stock", "ETF")
            - Country (str): country of listing
            - Currency (str): trading currency
            - ISIN (str): ISIN code
            - previousClose (float): last closing price
            - previousCloseDate (str): date of last close (YYYY-MM-DD)

        Examples:
            "Find Apple stock" → get_stocks_from_search(query="Apple Inc", type="stock")
            "Search for ISIN US0378331005" → get_stocks_from_search(query="US0378331005")
            "Crypto assets matching ETH" → get_stocks_from_search(query="ETH", type="crypto", limit=10)


        """
        # --- Validate ---
        if not query or not isinstance(query, str):
            raise ToolError("Parameter 'query' is required and must be a string.")
        if fmt != "json":
            raise ToolError("Only 'json' is supported for the Search API.")
        if not isinstance(limit, int) or not (1 <= limit <= 500):
            raise ToolError("'limit' must be an integer between 1 and 500.")
        if type is not None and type not in ALLOWED_TYPES:
            raise ToolError(f"Invalid 'type'. Allowed: {sorted(ALLOWED_TYPES)}")

        # --- Build URL ---
        # Endpoint shape: /api/search/{query_string}?fmt=json&limit=...&bonds_only=1&exchange=...&type=...
        encoded_query = quote(query, safe="")
        url = f"{EODHD_API_BASE}/search/{encoded_query}?fmt={fmt}&limit={limit}"

        if bonds_only:
            url += "&bonds_only=1"
        if exchange:
            url += f"&exchange={quote(str(exchange))}"
        if type:
            url += f"&type={quote(type)}"

        # Per-call token override (note: demo does NOT work for Search)
        if api_token:
            url += f"&api_token={api_token}"

        # --- Request ---
        data = await make_request(url)

        # --- Normalize / return ---
        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return format_json_response(data)
        except Exception:
            raise ToolError("Unexpected response format from API.")
