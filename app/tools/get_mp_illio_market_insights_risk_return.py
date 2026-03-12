# get_mp_illio_market_insights_risk_return.py

import json
from urllib.parse import quote_plus

from app.api_client import make_request
from app.config import EODHD_API_BASE
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


async def _run_risk_return(id: str, fmt: str, api_token: str | None) -> str:
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
    # Example: /api/mp/illio/chapters/risk/NDX?api_token=...&fmt=json
    url = f"{EODHD_API_BASE}/mp/illio/chapters/risk/{cid}?1=1"
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
        return json.dumps(data, indent=2)
    except Exception:
        raise ToolError("Unexpected JSON response format from API.")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_illio_market_insights_risk_return(
        id: str,  # one of {'SnP500','DJI','NDX'} (common aliases accepted)
        fmt: str = "json",  # JSON only (Marketplace returns JSON)
        api_token: str | None = None,  # per-call override (else env EODHD_API_KEY)
    ) -> str:
        """

        [Illio] Analyze market-level risk-return tradeoff for index constituents.
        Covers S&P 500, Dow Jones, and Nasdaq-100. Returns risk-adjusted return metrics,
        Sharpe-style analysis, and constituent risk-return scatter data. Consumes 10 API calls per request.
        For portfolio-level risk attributes, use mp_illio_risk_insights.
        For beta sensitivity analysis, use get_mp_illio_market_insights_beta_bands.


        Returns:
          JSON object with risk-return insight chapter data:
            - chapter (str): chapter identifier, e.g. "risk"
            - id (str): index identifier, e.g. "NDX"
            - data (object): risk-return analysis, including:
                - scatter (array): instruments plotted by risk vs return
                - quadrants (object): classification into high/low risk-return quadrants
                - summary (object|null): aggregate risk-return statistics
            - metadata (object|null): date range, benchmark info

        Limits (Marketplace rules):
          - 1 request = 10 API calls
          - 100k calls / 24h, 1k requests / minute
          - Output is JSON

        Examples:
            "S&P 500 risk-return insight" → id="SnP500"
            "Nasdaq-100 risk vs return" → id="NDX"


        """
        return await _run_risk_return(id=id, fmt=fmt, api_token=api_token)

    # Optional alias for convenience/back-compat
    @mcp.tool()
    async def mp_illio_market_insights_risk_return(
        id: str,
        fmt: str = "json",
        api_token: str | None = None,
    ) -> str:
        return await _run_risk_return(id=id, fmt=fmt, api_token=api_token)
