# app/tools/get_mp_illio_performance_insights.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)

# Canonical IDs as required by the endpoint
_ALLOWED_IDS = {"SnP500", "DJI", "NDX"}

# Optional convenience mapping to tolerate common variants (case-insensitive)
_CANONICAL_MAP = {
    "SNP500": "SnP500",
    "SNP-500": "SnP500",
    "S&P500": "SnP500",
    "SP500": "SnP500",
    "SPX": "SnP500",
    "DJI": "DJI",
    "DOW": "DJI",
    "NDX": "NDX",
    "NASDAQ-100": "NDX",
    "NASDAQ100": "NDX",
}


def _canon_id(v: str) -> str | None:
    if not isinstance(v, str) or not v.strip():
        return None
    s = v.strip()
    if s in _ALLOWED_IDS:
        return s
    # case-insensitive convenience normalization
    k = s.upper().replace(" ", "")
    return _CANONICAL_MAP.get(k)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_illio_performance_insights(
        id: str,  # one of {'SnP500','DJI','NDX'} (common aliases accepted)
        fmt: str = "json",  # JSON only (Marketplace returns JSON)
        api_token: str | None = None,  # per-call override (else env EODHD_API_KEY)
    ) -> ResourceResponse:
        """

        [Illio] Retrieve portfolio-level performance attributes for a major US index.
        Covers S&P 500, Dow Jones, and Nasdaq-100. Returns return metrics, attribution,
        and performance breakdown at the index-portfolio level. Consumes 10 API calls per request.
        For market-level performance comparison across constituents, use get_mp_illio_market_insights_performance.
        For risk attributes of the same indices, use mp_illio_risk_insights.

        Args:
          id: 'SnP500' | 'DJI' | 'NDX'  (common aliases like 'SP500', 'SPX', 'NASDAQ100' accepted)
          fmt: 'json' only (kept for symmetry with other tools)
          api_token: override token; otherwise picked from environment by make_request()

        Returns:
          JSON object with performance attributes for the selected index:
            - category (str): category name, e.g. "performance"
            - id (str): index identifier, e.g. "SnP500"
            - attributes (array): list of performance attribute objects, each containing:
                - name (str): attribute name (e.g. "1W Return", "1M Return", "YTD Return")
                - value (float|null): current attribute value
                - details (object|null): additional breakdown or metadata
          On failure returns ToolError.

        Examples:
            "S&P 500 performance insights" → id="SnP500"
            "Nasdaq-100 performance attributes" → id="NDX"


        """
        # Validate fmt
        fmt = (fmt or "json").lower()
        if fmt != "json":
            raise ToolError("Only JSON is supported for this endpoint (fmt must be 'json').")

        # Validate/normalize id
        cid = _canon_id(id)
        if cid is None:
            raise ToolError(
                "Invalid 'id'. Allowed: ['SnP500', 'DJI', 'NDX'] (aliases like 'SP500', 'SPX', 'NASDAQ100' accepted)."
            )

        # Build URL
        # Example: /api/mp/illio/categories/performance/SnP500?api_token=...&fmt=json
        url = build_url(f"mp/illio/categories/performance/{cid}", {"fmt": "json", "api_token": api_token})

        # Call upstream
        data = await make_request(url)

        # Normalize and return
        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected JSON response format from API.") from e
