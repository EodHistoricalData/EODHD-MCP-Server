# app/tools/get_stock_market_logos_svg.py

from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, sanitize_ticker
from app.response_formatter import ResourceResponse, format_text_response, raise_on_api_error


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_stock_market_logos_svg(
        symbol: str,  # e.g. "AAPL.US", "RY.TO"
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Get a company logo in SVG vector format. Use when the user needs a scalable vector logo
        for high-quality rendering, web embedding, or print.

        Limited to US and TO (Toronto) exchanges only. Costs 10 API calls per request.
        Symbol must be in TICKER.EXCHANGE format (e.g., 'AAPL.US', 'RY.TO').

        For PNG logos with broader exchange coverage (60+ exchanges), use get_stock_market_logos.

        Args:
            symbol (str): Ticker in TICKER.EXCHANGE format (e.g. 'AAPL.US', 'RY.TO').
            api_token (str, optional): Per-call token override.


        Returns:
            SVG image data as XML string (vector logo, scalable).

        Notes:
            - Marketplace product: 10 API calls per request.
            - Response is SVG image data (XML text).
            - Limited to US and TO exchanges.

        Examples:
            "Apple SVG logo" → get_stock_market_logos_svg(symbol="AAPL.US")
            "Royal Bank of Canada vector logo" → get_stock_market_logos_svg(symbol="RY.TO")
        """
        symbol = sanitize_ticker(symbol, param_name="symbol").upper()

        url = build_url(f"logo-svg/{quote_plus(symbol)}", {"api_token": api_token})

        data = await make_request(url, response_mode="text")
        raise_on_api_error(data)

        if not isinstance(data, str) or not data:
            raise ToolError("Unexpected response format from API.")

        return format_text_response(data, "image/svg+xml", resource_path=f"logos/{quote_plus(symbol)}.svg")
