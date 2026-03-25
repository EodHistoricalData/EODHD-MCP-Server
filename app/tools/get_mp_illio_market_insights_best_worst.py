# app/tools/get_mp_illio_market_insights_best_worst.py

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


async def _run_best_worst(id: str, fmt: str, api_token: str | None) -> ResourceResponse:
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
    # Example: /api/mp/illio/chapters/best-and-worst/NDX?api_token=...&fmt=json
    url = build_url(
        f"mp/illio/chapters/best-and-worst/{cid}",
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
    async def get_mp_illio_market_insights_best_worst(
        id: str,  # one of {'SnP500','DJI','NDX'} (common aliases accepted)
        fmt: str = "json",  # JSON only (Marketplace returns JSON)
        api_token: str | None = None,  # per-call override (else env EODHD_API_KEY)
    ) -> ResourceResponse:
        """

        [Illio] Get the largest single-day gains and losses for index constituents.
        Covers S&P 500, Dow Jones, and Nasdaq-100. Returns best and worst 1-day moves
        with dates, magnitudes, and affected instruments. Consumes 10 API calls per request.
        For overall constituent performance, use get_mp_illio_market_insights_performance.
        For volatility trends, use get_mp_illio_market_insights_volatility.


        Returns:
          JSON object with largest single-day moves chapter data:
            - chapter (str): chapter identifier, e.g. "best-and-worst"
            - id (str): index identifier, e.g. "NDX"
            - data (object): contains best/worst day arrays, each entry with:
                - ticker (str): instrument symbol
                - name (str): instrument name
                - date (str): date of the move
                - change (float): percentage change on that day
            - metadata (object|null): date range, benchmark info

        Limits (Marketplace rules):
          - 1 request = 10 API calls
          - 100k calls / 24h, 1k requests / minute
          - Output is JSON

        Examples:
            "S&P 500 best and worst days" → id="SnP500"
            "Nasdaq-100 largest single-day moves" → id="NDX"


        """
        return await _run_best_worst(id=id, fmt=fmt, api_token=api_token)
