# app/tools/get_mp_us_options_contracts.py

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


def _q_fields_contracts(fields: str | Sequence[str] | None) -> str:
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
        underlying_symbol: str | None = None,  # filter[underlying_symbol]
        contract: str | None = None,  # filter[contract]
        exp_date_eq: str | None = None,  # filter[exp_date_eq]    YYYY-MM-DD
        exp_date_from: str | None = None,  # filter[exp_date_from]  YYYY-MM-DD
        exp_date_to: str | None = None,  # filter[exp_date_to]    YYYY-MM-DD
        tradetime_eq: str | None = None,  # filter[tradetime_eq]   YYYY-MM-DD
        tradetime_from: str | None = None,  # filter[tradetime_from] YYYY-MM-DD
        tradetime_to: str | None = None,  # filter[tradetime_to]   YYYY-MM-DD
        type: str | None = None,  # filter[type] 'put'|'call'
        strike_eq: float | None = None,  # filter[strike_eq]
        strike_from: float | None = None,  # filter[strike_from]
        strike_to: float | None = None,  # filter[strike_to]
        sort: str | None = None,  # exp_date|strike|-exp_date|-strike
        page_offset: int = 0,  # page[offset] 0..10000
        page_limit: int = 1000,  # page[limit]  1..1000
        fields: str | Sequence[str] | None = None,  # fields[options-contracts]
        api_token: str | None = None,
        fmt: str | None = "json",
    ) -> ResourceResponse:
        """

        [Marketplace] Get available US options contracts (calls and puts) for a stock or ETF.
        Returns strike prices, expiration dates, and contract symbols for the specified underlying ticker.
        Supports filtering by expiration date range, strike range, trade time, and option type (put/call).
        Use to discover which options exist before fetching pricing with get_us_options_eod.
        For the list of all tickers that have options, use get_us_options_underlyings.
        Consumes 10 API calls per request.


        Returns:
            JSON object with:
            - meta: Pagination metadata.
            - data (array): Options contracts, each with:
              - contractName (str): Full OCC contract name.
              - contractSize (int): Contract size (typically 100).
              - currency (str): Currency code (e.g. 'USD').
              - type (str): 'call' or 'put'.
              - lastTradeDateTime (str): Last trade timestamp.
              - strike (float): Strike price.
              - lastPrice (float): Last traded price.
              - bid (float): Current bid price.
              - ask (float): Current ask price.
              - volume (int): Trading volume.
              - openInterest (int): Open interest.
              - impliedVolatility (float): Implied volatility.
              - delta (float): Option delta.
              - gamma (float): Option gamma.
              - theta (float): Option theta.
              - vega (float): Option vega.
              - expirationDate (str): Expiration date YYYY-MM-DD.
              - daysBeforeExpiration (int): Days until expiration.
              - intrinsicValue (float): Intrinsic value.
            - links.next (str|null): URL for next page, null if last page.

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
            "mp/unicornbay/options/contracts",
            {
                "sort": sort,
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
        url += _q_fields_contracts(fields)

        data = await make_request(url)

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
