# app/tools/resolve_ticker.py

import logging
from urllib.parse import quote

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, sanitize_exchange
from app.response_formatter import ResourceResponse, format_json_response, raise_on_api_error

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def resolve_ticker(
        query: str,
        preferred_exchange: str | None = None,
        asset_type: str | None = None,
        api_token: str | None = None,
    ) -> ResourceResponse:
        """
        Resolve a company name, partial ticker, or ISIN to SYMBOL.EXCHANGE format (and ISIN).

        USE THIS FIRST when a user mentions a company by name instead of a ticker symbol,
        or when you need to obtain the ISIN for a company/ticker.
        Calls the EODHD Search API and returns the best match as SYMBOL.EXCHANGE plus ISIN.
        If ambiguous (multiple exchanges), returns top 10 matches for user selection.

        Examples:
            "Apple" → query="Apple"
            "Tesla on NASDAQ" → query="Tesla", preferred_exchange="US"
            "ISIN US0378331005" → query="US0378331005"
            "Deutsche Bank on XETRA" → query="Deutsche Bank", preferred_exchange="XETRA"

        Args:
            query (str): Company name, partial ticker, or ISIN to resolve.
            preferred_exchange (str, optional): Exchange code to prefer (e.g. "US", "XETRA", "LSE").
            asset_type (str, optional): Filter by type: "stock", "etf", "fund", "bond", "index", "crypto".
            api_token (str, optional): Per-call API token override.

        Returns:
            JSON object with:
            - resolved (str): best-match ticker in SYMBOL.EXCHANGE format (e.g. "AAPL.US")
            - name (str): full company/instrument name
            - isin (str): ISIN code (e.g. "US0378331005")
            - type (str): asset type (Common Stock, ETF, etc.)
            - exchange (str): exchange code
            - alternatives (list): if ambiguous, top 10 matches each with ticker, name, isin, type, exchange

        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        if not query or not isinstance(query, str):
            raise ToolError("Parameter 'query' is required and must be a non-empty string.")

        if isinstance(preferred_exchange, str) and not preferred_exchange.strip():
            preferred_exchange = None
        elif preferred_exchange is not None:
            preferred_exchange = sanitize_exchange(preferred_exchange, param_name="preferred_exchange")

        allowed = {"stock", "etf", "fund", "bond", "index", "crypto"}
        if asset_type and asset_type not in allowed:
            raise ToolError(f"Invalid 'asset_type'. Allowed: {sorted(allowed)}")

        encoded_query = quote(query.strip(), safe="")
        url = build_url(
            f"search/{encoded_query}",
            {
                "fmt": "json",
                "limit": 10,
                "type": asset_type,
                "exchange": preferred_exchange,
                "api_token": api_token,
            },
        )

        data = await make_request(url)
        raise_on_api_error(data)

        if data is None:
            raise ToolError("No response from API.")
        if not isinstance(data, list):
            raise ToolError("Unexpected response format from API.")
        if len(data) == 0:
            return format_json_response({"resolved": None, "message": f"No results found for '{query}'."})

        best = data[0]
        resolved = f"{best.get('Code', '')}.{best.get('Exchange', '')}"

        # Check if results are ambiguous (same name, different exchanges)
        alternatives = []
        if len(data) > 1:
            seen = set()
            for item in data[:15]:
                key = f"{item.get('Code')}.{item.get('Exchange')}"
                if key not in seen and key != resolved:
                    seen.add(key)
                    alternatives.append(
                        {
                            "ticker": key,
                            "name": item.get("Name", ""),
                            "isin": item.get("ISIN", ""),
                            "type": item.get("Type", ""),
                            "exchange": item.get("Exchange", ""),
                        }
                    )

        result = {
            "resolved": resolved,
            "name": best.get("Name", ""),
            "isin": best.get("ISIN", ""),
            "type": best.get("Type", ""),
            "exchange": best.get("Exchange", ""),
        }

        if alternatives:
            result["alternatives"] = alternatives[:10]

        return format_json_response(result)
