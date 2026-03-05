#get_stock_market_logos_svg.py

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
    async def get_stock_market_logos_svg(
        symbol: str,                            # e.g. "AAPL.US", "RY.TO"
        api_token: Optional[str] = None,        # per-call override
    ) -> str:
        """
        Stock Market Logos API (SVG)
        GET /api/logo-svg/{symbol}

        Returns an SVG vector logo for the given symbol.
        Coverage: US and TO (Toronto) exchanges only.

        Args:
            symbol (str): Ticker in {TICKER}.{EXCHANGE} format (e.g. 'AAPL.US', 'RY.TO').
            api_token (str, optional): Per-call token override; env token used otherwise.

        Notes:
            - Marketplace product: 10 API calls per request.
            - Response is SVG image data (XML text).
            - Limited to US and TO exchanges.
        """
        if not symbol or not isinstance(symbol, str):
            raise ToolError(
                "Parameter 'symbol' is required in {TICKER}.{EXCHANGE} format "
                "(e.g. 'AAPL.US', 'RY.TO')."
            )

        symbol = symbol.strip().upper()

        url = f"{EODHD_API_BASE}/logo-svg/{quote_plus(symbol)}?1=1"
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
