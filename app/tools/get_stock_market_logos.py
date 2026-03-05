#get_stock_market_logos.py

import json
from typing import Optional
from urllib.parse import quote_plus

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_stock_market_logos(
        symbol: str,                            # e.g. "AAPL.US", "BMW.XETRA"
        api_token: Optional[str] = None,        # per-call override
    ) -> str:
        """
        Stock Market Logos API (PNG)
        GET /api/logo/{symbol}

        Returns a 200x200 PNG logo with transparency for the given symbol.
        Coverage: 40,000+ logos across 60+ exchanges.

        Args:
            symbol (str): Ticker in {TICKER}.{EXCHANGE} format (e.g. 'AAPL.US', 'BMW.XETRA').
            api_token (str, optional): Per-call token override; env token used otherwise.

        Notes:
            - Marketplace product: 10 API calls per request.
            - Response is a binary PNG image.
            - Supported exchanges include: AS, AT, AU, BA, BK, BR, BSE, CN, CO, CSE,
              DU, F, HE, HK, HM, IC, IR, IS, JK, JSE, KLSE, KO, KQ, LS, LSE, MC,
              MCX, MI, MU, MX, NEO, NSE, NZ, OL, PA, RG, SA, SG, SHE, SHG, SN, SR,
              ST, STU, SW, TA, TO, TSE, TW, TWO, US, V, VI, VS, VX, XETRA.
        """
        if not symbol or not isinstance(symbol, str):
            return _err(
                "Parameter 'symbol' is required in {TICKER}.{EXCHANGE} format "
                "(e.g. 'AAPL.US', 'BMW.XETRA')."
            )

        symbol = symbol.strip().upper()

        url = f"{EODHD_API_BASE}/logo/{quote_plus(symbol)}?1=1"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected response format from API.")
