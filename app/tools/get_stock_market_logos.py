#get_stock_market_logos.py

import json
from typing import Optional
from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_stock_market_logos(
        symbol: str,                            # e.g. "AAPL.US", "BMW.XETRA"
        api_token: Optional[str] = None,        # per-call override
    ) -> str:
        """
        Get a company logo in PNG format (200x200 with transparency). Use when the user needs
        a raster logo image for a stock or company for display, reports, or UI.

        Covers 40,000+ logos across 60+ exchanges. Costs 10 API calls per request.
        Symbol must be in TICKER.EXCHANGE format (e.g., 'AAPL.US', 'BMW.XETRA').

        For vector/SVG logos (US and Toronto only), use get_stock_market_logos_svg instead.

        Args:
            symbol (str): Ticker in TICKER.EXCHANGE format (e.g. 'AAPL.US', 'BMW.XETRA').
            api_token (str, optional): Per-call token override.
        """
        if not symbol or not isinstance(symbol, str):
            raise ToolError(
                "Parameter 'symbol' is required in {TICKER}.{EXCHANGE} format "
                "(e.g. 'AAPL.US', 'BMW.XETRA')."
            )

        symbol = symbol.strip().upper()

        url = f"{EODHD_API_BASE}/logo/{quote_plus(symbol)}?1=1"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
