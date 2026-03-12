# get_mp_praams_bond_analyze_by_isin.py

from urllib.parse import quote_plus

from app.api_client import make_request
from app.config import EODHD_API_BASE
from app.response import format_json_response
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def _q(key: str, val: str | int | None) -> str:
    """
    Helper to build query parameters safely.
    Skips None/empty, URL-encodes values.
    """
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def _canon_isin(v: str) -> str | None:
    """
    Very light validation/normalization for Praams bond ISIN path param.

    Docs show usage like:
      /api/mp/praams/analyse/bond/US7593518852

    We:
      - Require a non-empty string
      - Strip surrounding whitespace
      - Uppercase alpha characters (ISINs are conventionally uppercase).
    """
    if not isinstance(v, str):
        return None
    s = v.strip()
    if not s:
        return None
    return s.upper()


async def _run_praams_bond_by_isin(isin: str, api_token: str | None) -> list:
    """
    Core runner for Praams Bond Risk & Return analysis by ISIN.


        Examples:
            "Analyze US Treasury bond" → isin="US912810TM53"
            "Realty Income bond risk analysis" → isin="US7593518852"

    """
    # Validate/normalize ISIN
    ci = _canon_isin(isin)
    if ci is None:
        raise ToolError("Invalid 'isin'. It must be a non-empty string (e.g., 'US7593518852').")

    # Build URL
    # Example: /api/mp/praams/analyse/bond/US7593518852?api_token=...  (JSON only)
    url = f"{EODHD_API_BASE}/mp/praams/analyse/bond/{ci}?1=1"
    if api_token:
        url += _q("api_token", api_token)  # otherwise appended by make_request via env

    # Call upstream
    data = await make_request(url)
    if data is None:
        raise ToolError("No response from API.")

    if isinstance(data, dict) and data.get("error"):
        raise ToolError(str(data["error"]))
    # Normalize and return
    # The Praams bond API wraps the payload in: {"success": ..., "item": {...}, "errors": [...]}
    # We just pretty-print whatever comes back.
    try:
        return format_json_response(data)
    except Exception:
        raise ToolError("Unexpected JSON response format from API.")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_praams_bond_analyze_by_isin(
        isin: str,  # e.g. 'US7593518852' (demo supports US7593518852, US91282CJN20)
        api_token: str | None = None,  # per-call override (else env EODHD_API_KEY)
    ) -> list:
        """

        [PRAAMS] Get deep risk-return analysis for a bond identified by ISIN code.
        Returns PRAAMS ratio, coupon profile, credit/solvency assessment, stress-test results,
        volatility, liquidity, country risk narratives, and issuer-level fundamentals.
        Use for detailed bond-specific due diligence. Consumes 10 API calls per request.
        For bond screening across multiple instruments, use get_mp_praams_smart_screener_bond.
        For a full PDF bond report, use get_mp_praams_report_bond_by_isin.

        Returns:
          JSON object with Praams envelope:
            - success (bool): whether the request succeeded
            - item (object): bond analysis payload containing:
                - praamsRatio (float): overall PRAAMS score
                - totalReturnScore (int): aggregate return score (1-7 scale)
                - totalRiskScore (int): aggregate risk score (1-7 scale)
                - coupon (object): coupon profile (type, rate, frequency, structure notes)
                - valuation (object): yield-to-maturity, spread, price metrics
                - performance (object): price and total return performance
                - profitability (object): issuer-level profitability metrics
                - growthMomentum (object): issuer growth & momentum
                - marketView (object): spread history, yield curve positioning
                - volatility (object): price volatility, duration-adjusted risk
                - stressTest (object): stress-test scenarios and score
                - liquidity (object): trading volume, bid-ask spread, score
                - countryRisk (object): country-level risk assessment and score
                - solvency (object): issuer creditworthiness, leverage, coverage ratios
                - descriptions (object|null): narrative risk/return explanations
            - errors (array): list of error messages, empty on success
            - message (str): status message

        Limits (Marketplace rules):
          - 1 request = 10 API calls
          - 100k calls / 24h, 1k requests / minute
          - Output is JSON only

        """
        return await _run_praams_bond_by_isin(isin=isin, api_token=api_token)

    # Optional alias for convenience/back-compat (shorter name)
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_praams_bond_analyze_by_isin(
        isin: str,
        api_token: str | None = None,
    ) -> list:
        return await _run_praams_bond_by_isin(isin=isin, api_token=api_token)
