# app/tools/get_mp_illio_market_insights_volatility.py

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
    "DOW30": "DJI",
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


async def _run_volatility(id: str, fmt: str, api_token: str | None) -> ResourceResponse:
    # Validate fmt
    fmt = (fmt or "json").lower()
    if fmt != "json":
        raise ToolError("Only JSON is supported for this endpoint (fmt must be 'json').")

    # Validate/normalize id
    cid = _canon_id(id)
    if cid is None:
        raise ToolError(
            "Invalid 'id'. Allowed: ['SnP500', 'DJI', 'NDX'] "
            "(aliases like 'SP500', 'SPX', 'DOW', 'NASDAQ100' accepted)."
        )

    # Build URL
    # Example: /api/mp/illio/chapters/volatility/NDX?api_token=...&fmt=json
    url = build_url(f"mp/illio/chapters/volatility/{cid}", {"fmt": "json", "api_token": api_token})

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


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_illio_market_insights_volatility(
        id: str,  # one of {'SnP500','DJI','NDX'} (common aliases accepted)
        fmt: str = "json",  # JSON only (Marketplace returns JSON)
        api_token: str | None = None,  # per-call override (else env EODHD_API_KEY)
    ) -> ResourceResponse:
        """

        [Illio] Get volatility bands and daily move distribution for index constituents.
        Covers S&P 500, Dow Jones, and Nasdaq-100. Returns volatility levels, daily move
        ranges, and constituent volatility distribution versus market. Consumes 10 API calls per request.
        For largest year-over-year volatility changes, use get_mp_illio_market_insights_largest_volatility.
        For best/worst single-day moves, use get_mp_illio_market_insights_best_worst.


        Returns:
          JSON object with volatility bands chapter data:
            - chapter (str): chapter identifier, e.g. "volatility"
            - id (str): index identifier, e.g. "NDX"
            - data (object): volatility and day-move distributions, including:
                - bands (array): volatility band buckets with instrument counts
                - instruments (array): per-instrument volatility metrics
                - dailyMoves (object|null): distribution of daily price changes
            - metadata (object|null): date range, calculation parameters

        Limits (Marketplace rules):
          - 1 request = 10 API calls
          - 100k calls / 24h, 1k requests / minute
          - Output is JSON

        Examples:
            "Dow Jones volatility bands" → id="DJI"
            "Nasdaq-100 volatility and day moves" → id="NDX"


        """
        return await _run_volatility(id=id, fmt=fmt, api_token=api_token)
