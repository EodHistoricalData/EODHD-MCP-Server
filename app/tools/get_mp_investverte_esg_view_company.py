#get_mp_investverte_esg_view_company.py

import json
from typing import Optional, Union

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations

ALLOWED_FREQUENCIES = {"FY", "Q1", "Q2", "Q3", "Q4"}


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_investverte_esg_view_company(
        symbol: str,                          # e.g., "AAPL" or "000039.SZ"
        year: Optional[Union[int, str]] = None,   # e.g., 2021
        frequency: Optional[str] = None,          # one of ALLOWED_FREQUENCIES
        fmt: Optional[str] = "json",
        api_token: Optional[str] = None,          # per-call override
    ) -> str:
        """
        View ESG ratings for a specific company
        (GET /api/mp/investverte/esg/{SYMBOL})

        Examples:
            - /api/mp/investverte/esg/AAPL?year=2021&frequency=FY
            - /api/mp/investverte/esg/000039.SZ

        Returns:
            A JSON-formatted string with an array of objects, e.g.:

            [
              {
                "e": 58.97,
                "s": 68.66,
                "g": 65.21,
                "esg": 64.09,
                "year": 2021,
                "frequency": "FY"
              },
              ...
            ]

        Notes:
            - Year and frequency are optional; when omitted, all available
              years/frequencies for the symbol are returned.
            - Rate limits (Marketplace product):
                * 100,000 API calls per 24 hours
                * 1,000 API requests per minute
                * 1 API request = 10 API calls
        """
        if not symbol or not isinstance(symbol, str):
            return _err("Parameter 'symbol' is required and must be a non-empty string (e.g., 'AAPL').")

        if fmt != "json":
            return _err("Only 'json' is supported by this tool.")

        if frequency is not None and frequency not in ALLOWED_FREQUENCIES:
            return _err(f"Invalid 'frequency'. Allowed: {sorted(ALLOWED_FREQUENCIES)}")

        if year is not None and not isinstance(year, (int, str)):
            return _err("Parameter 'year' must be an integer or string representing a year, e.g., 2021.")

        # Base URL for Investverte company ESG endpoint
        url = f"{EODHD_API_BASE}/mp/investverte/esg/{symbol}?fmt={fmt}"

        if year is not None:
            url += f"&year={year}"
        if frequency:
            url += f"&frequency={frequency}"
        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            # Propagate API error message
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            # Expected: list of ESG entries for the company
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected response format from API.")

