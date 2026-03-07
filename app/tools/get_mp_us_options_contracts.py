#get_mp_us_options_contracts.py

import json
from typing import Optional, Union, Sequence
from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


ALLOWED_SORT = {"exp_date", "strike", "-exp_date", "-strike"}
ALLOWED_TYPE = {None, "put", "call"}
ALLOWED_FMT = {"json"}

def _q(key: str, val: Optional[Union[str, int, float]]) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def _q_bool(key: str, val: Optional[bool]) -> str:
    if val is None:
        return ""
    return f"&{key}={(1 if val else 0)}"


def _q_fields_contracts(fields: Optional[Union[str, Sequence[str]]]) -> str:
    """
    Build fields[options-contracts] param.

    Accepts:
      - None  -> no param
      - "field1,field2"
      - ["field1", "field2", ...]
    """
    if fields is None:
        return ""

    if isinstance(fields, str):
        value = fields.strip()
    else:
        # Be robust to non-string items in the sequence
        parts = [str(f).strip() for f in fields if f is not None and str(f).strip()]
        if not parts:
            return ""
        value = ",".join(parts)

    return f"&fields[options-contracts]={quote_plus(value)}"


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_us_options_contracts(
        underlying_symbol: Optional[str] = None,     # filter[underlying_symbol]
        contract: Optional[str] = None,              # filter[contract]
        exp_date_eq: Optional[str] = None,           # filter[exp_date_eq]    YYYY-MM-DD
        exp_date_from: Optional[str] = None,         # filter[exp_date_from]  YYYY-MM-DD
        exp_date_to: Optional[str] = None,           # filter[exp_date_to]    YYYY-MM-DD
        tradetime_eq: Optional[str] = None,          # filter[tradetime_eq]   YYYY-MM-DD
        tradetime_from: Optional[str] = None,        # filter[tradetime_from] YYYY-MM-DD
        tradetime_to: Optional[str] = None,          # filter[tradetime_to]   YYYY-MM-DD
        type: Optional[str] = None,                  # filter[type] 'put'|'call'
        strike_eq: Optional[float] = None,           # filter[strike_eq]
        strike_from: Optional[float] = None,         # filter[strike_from]
        strike_to: Optional[float] = None,           # filter[strike_to]
        sort: Optional[str] = None,                  # exp_date|strike|-exp_date|-strike
        page_offset: int = 0,                        # page[offset] 0..10000
        page_limit: int = 1000,                      # page[limit]  1..1000
        fields: Optional[Union[str, Sequence[str]]] = None,  # fields[options-contracts]
        api_token: Optional[str] = None,
        fmt: Optional[str] = "json",
    ) -> str:
        """
        [Marketplace] Get available US options contracts (calls and puts) for a stock or ETF.
        Returns strike prices, expiration dates, and contract symbols for the specified underlying ticker.
        Supports filtering by expiration date range, strike range, trade time, and option type (put/call).
        Use to discover which options exist before fetching pricing with get_us_options_eod.
        For the list of all tickers that have options, use get_us_options_underlyings.
        Consumes 10 API calls per request.


        Examples:
            "AAPL options expiring this month" → underlying_symbol="AAPL", exp_date_from="2026-03-01", exp_date_to="2026-03-31"
            "SPY puts with strike between 400 and 450" → underlying_symbol="SPY", type="put", strike_from=400, strike_to=450
            "TSLA call contracts expiring in June 2026, sorted by strike" → underlying_symbol="TSLA", type="call", exp_date_from="2026-06-01", exp_date_to="2026-06-30", sort="strike"

        """
        # --- validate ---
        if type not in ALLOWED_TYPE:
            raise ToolError("Invalid 'type'. Allowed: 'put', 'call' or omit.")
        if sort and sort not in ALLOWED_SORT:
            raise ToolError(f"Invalid 'sort'. Allowed: {sorted(ALLOWED_SORT)}")
        if not isinstance(page_offset, int) or not (0 <= page_offset <= 10000):
            raise ToolError("'page_offset' must be an integer between 0 and 10000.")
        if not isinstance(page_limit, int) or not (1 <= page_limit <= 1000):
            raise ToolError("'page_limit' must be an integer between 1 and 1000.")
        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed: {sorted(ALLOWED_FMT)}")

        base = f"{EODHD_API_BASE}/mp/unicornbay/options/contracts?1=1"
        # filters
        base += _q("filter[contract]", contract)
        base += _q("filter[underlying_symbol]", underlying_symbol)
        base += _q("filter[exp_date_eq]", exp_date_eq)
        base += _q("filter[exp_date_from]", exp_date_from)
        base += _q("filter[exp_date_to]", exp_date_to)
        base += _q("filter[tradetime_eq]", tradetime_eq)
        base += _q("filter[tradetime_from]", tradetime_from)
        base += _q("filter[tradetime_to]", tradetime_to)
        base += _q("filter[type]", type)
        base += _q("filter[strike_eq]", strike_eq)
        base += _q("filter[strike_from]", strike_from)
        base += _q("filter[strike_to]", strike_to)
        # sort & pagination
        base += _q("sort", sort)
        base += _q("page[offset]", page_offset)
        base += _q("page[limit]", page_limit)
        # fields
        base += _q_fields_contracts(fields)
        # token
        if api_token:
            base += _q("api_token", api_token)
        # format
        if fmt:
            base += _q("fmt", fmt)

        data = await make_request(base)

        if data is None:
            raise ToolError("No response from API.")

        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
