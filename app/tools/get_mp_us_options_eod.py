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
        Get end-of-day options data (mp/unicornbay/options/eod)

        Returns JSON: meta, data[], links.next; supports 'compact' mode.
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
