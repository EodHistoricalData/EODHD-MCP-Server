# get_mp_us_options_eod.py

import json
from collections.abc import Sequence
from urllib.parse import quote_plus

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

ALLOWED_SORT = {"exp_date", "strike", "-exp_date", "-strike"}
ALLOWED_TYPE = {None, "put", "call"}
ALLOWED_FMT = {"json"}


def _q(key: str, val: str | int | float | None) -> str:
    if val is None or val == "":
        return ""
    return f"&{key}={quote_plus(str(val))}"


def _q_bool(key: str, val: bool | None) -> str:
    if val is None:
        return ""
    return f"&{key}={(1 if val else 0)}"


def _q_fields_eod(fields: str | Sequence[str] | None) -> str:
    if fields is None:
        return ""
    if isinstance(fields, str):
        value = fields
    else:
        value = ",".join(f.strip() for f in fields if f and str(f).strip())
    return f"&fields[options-eod]={quote_plus(value)}"


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_us_options_eod(
        underlying_symbol: str | None = None,  # filter[underlying_symbol]
        contract: str | None = None,  # filter[contract]
        exp_date_eq: str | None = None,
        exp_date_from: str | None = None,
        exp_date_to: str | None = None,
        tradetime_eq: str | None = None,
        tradetime_from: str | None = None,
        tradetime_to: str | None = None,
        type: str | None = None,  # 'put' | 'call'
        strike_eq: float | None = None,
        strike_from: float | None = None,
        strike_to: float | None = None,
        sort: str | None = None,  # exp_date|strike|-exp_date|-strike
        page_offset: int = 0,
        page_limit: int = 1000,
        fields: str | Sequence[str] | None = None,  # fields[options-eod]
        compact: bool | None = None,  # compact=1 to minimize payload
        api_token: str | None = None,
        fmt: str | None = "json",
    ) -> str:
        """

        [Marketplace] Fetch end-of-day pricing data for US options contracts. Use when asked about
        options prices, Greeks, open interest, volume, or implied volatility for stock/ETF options.
        Returns OHLC, volume, open interest, and Greeks per contract per trading day.
        Supports filtering by underlying symbol, expiration, strike, type (put/call), and trade date range.
        If you only have a company name or ISIN, call resolve_ticker first.
        First find available contracts with get_us_options_contracts, then fetch pricing here.
        For the list of optionable tickers, use get_us_options_underlyings.
        Consumes 10 API calls per request.


        Returns:
            JSON object with:
            - meta: Pagination metadata.
            - data (array): EOD options records per date, each containing:
              - options.CALLS (array): Call contracts with:
                - contractName (str): Full OCC contract name.
                - expirationDate (str): Expiration date YYYY-MM-DD.
                - strike (float): Strike price.
                - lastPrice (float): Last traded price.
                - bid (float): Bid price.
                - ask (float): Ask price.
                - change (float): Price change.
                - changePercent (float): Price change percentage.
                - volume (int): Trading volume.
                - openInterest (int): Open interest.
                - impliedVolatility (float): Implied volatility.
              - options.PUTS (array): Put contracts (same fields as CALLS).
            - links.next (str|null): URL for next page, null if last page.

        Examples:
            "AAPL end-of-day options for March 2026" → underlying_symbol="AAPL", tradetime_from="2026-03-01", tradetime_to="2026-03-31"
            "MSFT puts EOD data, strike 300-400" → underlying_symbol="MSFT", type="put", strike_from=300, strike_to=400
            "NVDA calls expiring 2026-06-20, compact" → underlying_symbol="NVDA", type="call", exp_date_eq="2026-06-20", compact=True


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

        base = f"{EODHD_API_BASE}/mp/unicornbay/options/eod?1=1"
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
        # fields & compact
        base += _q_fields_eod(fields)
        base += _q_bool("compact", compact)
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
