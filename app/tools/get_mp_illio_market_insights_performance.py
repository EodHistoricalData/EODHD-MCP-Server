# get_mp_illio_market_insights_performance.py

from urllib.parse import quote_plus

from app.api_client import make_request
from app.config import EODHD_API_BASE
from app.response import format_json_response
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def _q(key: str, val: str | int | None) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


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


async def _run_market_insights(id: str, fmt: str, api_token: str | None) -> list:
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
    # Example: /api/mp/illio/chapters/performance/NDX?api_token=...&fmt=json
    url = f"{EODHD_API_BASE}/mp/illio/chapters/performance/{cid}?1=1"
    url += _q("fmt", "json")  # explicit for symmetry with other tools
    if api_token:
        url += _q("api_token", api_token)  # otherwise appended by make_request via env

    # Call upstream
    data = await make_request(url)
    if data is None:
        raise ToolError("No response from API.")

    if isinstance(data, dict) and data.get("error"):
        raise ToolError(str(data["error"]))
    # Normalize and return
    try:
        return format_json_response(data)
    except Exception:
        raise ToolError("Unexpected JSON response format from API.")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_illio_market_insights_performance(
        id: str,  # one of {'SnP500','DJI','NDX'} (common aliases accepted)
        fmt: str = "json",  # JSON only (Marketplace returns JSON)
        api_token: str | None = None,  # per-call override (else env EODHD_API_KEY)
    ) -> list:
        """

        [Illio] Analyze market-level performance of index constituents versus the overall market.
        Covers S&P 500, Dow Jones, and Nasdaq-100. Returns constituent performance comparison,
        sector attribution, and relative performance data. Consumes 10 API calls per request.
        For portfolio-level performance attributes, use mp_illio_performance_insights.
        For best/worst single-day moves, use get_mp_illio_market_insights_best_worst.


        Returns:
          JSON object with performance-vs-market chapter data:
            - chapter (str): chapter identifier, e.g. "performance"
            - id (str): index identifier, e.g. "NDX"
            - data (array): time-series or tabular entries with instrument-level
              performance metrics vs the overall market (returns, relative strength)
            - metadata (object|null): chart config, date range, benchmark info

        Limits (Marketplace rules):
          - 1 request = 10 API calls
          - 100k calls / 24h, 1k requests / minute
          - Output is JSON

        Examples:
            "S&P 500 performance vs market" → id="SnP500"
            "Nasdaq-100 market performance chapter" → id="NDX"


        """
        return await _run_market_insights(id=id, fmt=fmt, api_token=api_token)

    # Back-compat alias so older tests/config keep working
    @mcp.tool()
    async def mp_illio_market_insights(
        id: str,
        fmt: str = "json",
        api_token: str | None = None,
    ) -> list:
        return await _run_market_insights(id=id, fmt=fmt, api_token=api_token)
