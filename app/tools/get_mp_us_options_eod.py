# app/tools/get_mp_us_options_eod.py

import logging
from collections.abc import Sequence
from urllib.parse import quote_plus

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_query_param, build_url, coerce_date_param, sanitize_ticker, validate_date_range
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)

ALLOWED_SORT = {"exp_date", "strike", "-exp_date", "-strike"}
ALLOWED_TYPE = {None, "put", "call"}
ALLOWED_FMT = {"json"}


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
    ) -> ResourceResponse:
        """

        [Marketplace] Fetch end-of-day pricing data for US options contracts. Use when asked about
        options prices, Greeks, open interest, volume, or implied volatility for stock/ETF options.
        Returns OHLC, volume, open interest, and Greeks per contract per trading day.
        Supports filtering by underlying symbol, expiration, strike, type (put/call), and trade date range.
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

        # --- coerce dates ---
        exp_date_eq = coerce_date_param(exp_date_eq, "exp_date_eq")
        exp_date_from = coerce_date_param(exp_date_from, "exp_date_from")
        exp_date_to = coerce_date_param(exp_date_to, "exp_date_to")
        validate_date_range(exp_date_from, exp_date_to, "exp_date_from", "exp_date_to")
        tradetime_eq = coerce_date_param(tradetime_eq, "tradetime_eq")
        tradetime_from = coerce_date_param(tradetime_from, "tradetime_from")
        tradetime_to = coerce_date_param(tradetime_to, "tradetime_to")
        validate_date_range(tradetime_from, tradetime_to, "tradetime_from", "tradetime_to")

        if isinstance(underlying_symbol, str) and not underlying_symbol.strip():
            underlying_symbol = None
        elif underlying_symbol is not None:
            underlying_symbol = sanitize_ticker(underlying_symbol, param_name="underlying_symbol")

        if isinstance(contract, str) and not contract.strip():
            contract = None
        elif contract is not None:
            contract = sanitize_ticker(contract, param_name="contract")

        # build_url handles non-bracket params; bracket-keyed params appended via build_query_param
        # (urlencode would percent-encode [ and ] in keys, breaking filter[*] and page[*])
        url = build_url(
            "mp/unicornbay/options/eod",
            {
                "sort": sort,
                "compact": compact,
                "api_token": api_token,
                "fmt": fmt,
            },
        )
        url += build_query_param("filter[contract]", contract)
        url += build_query_param("filter[underlying_symbol]", underlying_symbol)
        url += build_query_param("filter[exp_date_eq]", exp_date_eq)
        url += build_query_param("filter[exp_date_from]", exp_date_from)
        url += build_query_param("filter[exp_date_to]", exp_date_to)
        url += build_query_param("filter[tradetime_eq]", tradetime_eq)
        url += build_query_param("filter[tradetime_from]", tradetime_from)
        url += build_query_param("filter[tradetime_to]", tradetime_to)
        url += build_query_param("filter[type]", type)
        url += build_query_param("filter[strike_eq]", strike_eq)
        url += build_query_param("filter[strike_from]", strike_from)
        url += build_query_param("filter[strike_to]", strike_to)
        url += build_query_param("page[offset]", page_offset)
        url += build_query_param("page[limit]", page_limit)
        url += _q_fields_eod(fields)

        data = await make_request(url)

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
