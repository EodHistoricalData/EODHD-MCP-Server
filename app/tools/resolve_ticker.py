# app/tools/resolve_ticker.py

from urllib.parse import quote

from app.api_client import make_request
from app.config import EODHD_API_BASE
from app.response import format_json_response
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def resolve_ticker(
        query: str,
        preferred_exchange: str | None = None,
        asset_type: str | None = None,
        api_token: str | None = None,
    ) -> list:
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
        """
        if not query or not isinstance(query, str):
            raise ToolError("Parameter 'query' is required and must be a non-empty string.")

        encoded_query = quote(query.strip(), safe="")
        url = f"{EODHD_API_BASE}/search/{encoded_query}?fmt=json&limit=10"

        if asset_type:
            allowed = {"stock", "etf", "fund", "bond", "index", "crypto"}
            if asset_type not in allowed:
                raise ToolError(f"Invalid 'asset_type'. Allowed: {sorted(allowed)}")
            url += f"&type={quote(asset_type)}"

        if preferred_exchange:
            url += f"&exchange={quote(str(preferred_exchange))}"

        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from Search API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))
        if not isinstance(data, list) or len(data) == 0:
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
