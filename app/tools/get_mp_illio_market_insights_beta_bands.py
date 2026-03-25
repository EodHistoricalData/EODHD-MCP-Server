# app/tools/get_mp_illio_market_insights_beta_bands.py

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


async def _run_beta_bands(id: str, fmt: str, api_token: str | None) -> ResourceResponse:
    """
    Internal runner for Beta Bands chapter.


        Examples:
            "S&P 500 beta bands" → id="SnP500"
            "Nasdaq-100 highest and lowest beta stocks" → id="NDX"

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
    # Endpoint per docs:
    #   /api/mp/illio/chapters/beta-bands/{id}
    # Example:
    #   /api/mp/illio/chapters/beta-bands/NDX?api_token=...&fmt=json
    url = build_url(
        f"mp/illio/chapters/beta-bands/{cid}",
        {
            "fmt": "json",
            "api_token": api_token,
        },
    )

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
    async def get_mp_illio_market_insights_beta_bands(
        id: str,  # one of {'SnP500','DJI','NDX'} (common aliases accepted)
        fmt: str = "json",  # JSON only (Marketplace returns JSON)
        api_token: str | None = None,  # per-call override (else env EODHD_API_KEY)
    ) -> ResourceResponse:
        """

        [Illio] Analyze beta sensitivity distribution of index constituents relative to the market.
        Covers S&P 500, Dow Jones, and Nasdaq-100. Returns beta bracket distribution, instruments with
        highest/lowest beta, and how constituents react to overall market moves. Consumes 10 API calls per request.
        For risk-return tradeoff analysis, use get_mp_illio_market_insights_risk_return.
        For volatility trends, use get_mp_illio_market_insights_volatility.

        Returns:
          JSON object with beta bands chapter data:
            - chapter (str): chapter identifier, e.g. "beta-bands"
            - id (str): index identifier, e.g. "NDX"
            - data (object): beta distribution analysis, including:
                - bands (array): beta bracket ranges with instrument counts/percentages
                - highest (array): instruments with highest beta (most market-sensitive)
                - lowest (array): instruments with lowest beta (least market-sensitive)
                Each instrument entry includes: ticker, name, beta (float)
            - metadata (object|null): date range, calculation parameters

        Limits (Marketplace rules):
          - 1 request = 10 API calls
          - 100k calls / 24h, 1k requests / minute
          - Output is JSON

        """
        return await _run_beta_bands(id=id, fmt=fmt, api_token=api_token)
