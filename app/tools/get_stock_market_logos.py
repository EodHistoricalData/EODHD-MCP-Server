# app/tools/get_stock_market_logos.py

from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, sanitize_ticker
from app.response_formatter import ResourceResponse, format_binary_response, raise_on_api_error


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_stock_market_logos(
        symbol: str,  # e.g. "AAPL.US", "BMW.XETRA"
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Get a company logo in PNG format (200x200 with transparency). Use when the user needs
        a raster logo image for a stock or company for display, reports, or UI.

        Covers 40,000+ logos across 60+ exchanges. Costs 10 API calls per request.
        Symbol must be in TICKER.EXCHANGE format (e.g., 'AAPL.US', 'BMW.XETRA').

        For vector/SVG logos (US and Toronto only), use get_stock_market_logos_svg instead.

        Args:
            symbol (str): Ticker in TICKER.EXCHANGE format (e.g. 'AAPL.US', 'BMW.XETRA').
            api_token (str, optional): Per-call token override.


        Returns:
            Binary PNG image data (200x200 with transparency).
            When returned via JSON wrapper, base64-encoded image string.

        Notes:
            - Marketplace product: 10 API calls per request.
            - Response is a binary PNG image.
            - Supported exchanges include: AS, AT, AU, BA, BK, BR, CO, CSE,
              DU, F, HE, HK, HM, IC, IR, JK, JSE, KLSE, KO, KQ, LS, LSE, MC,
              MU, MX, NEO, OL, PA, SHE, SHG, SN, SA,
              ST, STU, SW, TA, TO, TW, TWO, US, V, VI, VS, VX, XETRA.

        Examples:
            "Apple logo" → get_stock_market_logos(symbol="AAPL.US")
            "BMW logo from XETRA" → get_stock_market_logos(symbol="BMW.XETRA")
        """
        symbol = sanitize_ticker(symbol, param_name="symbol").upper()

        url = build_url(f"logo/{quote_plus(symbol)}", {"api_token": api_token})

        data = await make_request(url, response_mode="bytes")
        raise_on_api_error(data)

        if not isinstance(data, bytes) or not data:
            raise ToolError("Unexpected response format from API.")

        return format_binary_response(data, "image/png", resource_path=f"logos/{quote_plus(symbol)}.png")
