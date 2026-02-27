#get_technical_indicators.py
import json
import re
from datetime import datetime
from typing import Optional, Union

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_ORDER = {"a", "d"}                 # ascending, descending (per docs)
ALLOWED_FMT = {"json", "csv"}
ALLOWED_AGG_PERIOD = {"d", "w", "m"}       # for splitadjusted only
PERIOD_MIN, PERIOD_MAX = 2, 100_000

# Canonical function list + convenience normalization
ALLOWED_FUNCTIONS = {
    "splitadjusted",
    "avgvol",
    "avgvolccy",
    "sma",
    "ema",
    "wma",
    "volatility",
    "stochastic",
    "rsi",
    "stddev",
    "stochrsi",
    "slope",
    "dmi",               # aka dx
    "adx",
    "macd",
    "atr",
    "cci",
    "sar",
    "beta",
    "bbands",
    "format_amibroker",
}

FUNC_ALIASES = {
    "dx": "dmi",
}

# splitadjusted_only is documented to work with these functions:
SPLITADJ_ONLY_SUPPORTED = {
    "sma", "ema", "wma", "volatility", "rsi", "slope", "macd",
}

def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)

def _valid_date(s: str) -> bool:
    if not isinstance(s, str) or not DATE_RE.match(s):
        return False
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def _normalize_function(fn: str) -> Optional[str]:
    if not isinstance(fn, str) or not fn.strip():
        return None
    f = fn.strip().lower()
    f = FUNC_ALIASES.get(f, f)
    return f if f in ALLOWED_FUNCTIONS else None

def _validate_period(name: str, val: Optional[Union[int, str]]) -> Optional[str]:
    if val is None or val == "":
        return None
    try:
        ival = int(val)
    except Exception:
        return f"Parameter '{name}' must be an integer."
    if not (PERIOD_MIN <= ival <= PERIOD_MAX):
        return f"Parameter '{name}' out of range [{PERIOD_MIN}, {PERIOD_MAX}]."
    return None

def _validate_float(name: str, val: Optional[Union[int, float, str]]) -> Optional[str]:
    if val is None or val == "":
        return None
    try:
        float(val)
    except Exception:
        return f"Parameter '{name}' must be a number."
    return None

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_technical_indicators(
        ticker: str,
        function: str,                          # required (e.g., 'sma', 'macd', 'stochastic', ...)
        # common optional
        start_date: Optional[str] = None,        # 'from' (YYYY-MM-DD)
        end_date: Optional[str] = None,          # 'to'   (YYYY-MM-DD)
        order: str = "a",                        # 'a' | 'd'
        fmt: str = "json",                       # 'json' | 'csv'
        filter: Optional[str] = None,            # e.g., 'last_ema', 'last_volume'
        splitadjusted_only: Optional[Union[int, bool, str]] = None,  # 0/1 or bool (only for some functions)

        # shared indicator params
        period: Optional[Union[int, str]] = None,

        # splitadjusted
        agg_period: Optional[str] = None,        # 'd'|'w'|'m' (splitadjusted only)

        # stochastic
        fast_kperiod: Optional[Union[int, str]] = None,
        slow_kperiod: Optional[Union[int, str]] = None,
        slow_dperiod: Optional[Union[int, str]] = None,

        # stochrsi
        fast_dperiod: Optional[Union[int, str]] = None,

        # macd
        fast_period: Optional[Union[int, str]] = None,
        slow_period: Optional[Union[int, str]] = None,
        signal_period: Optional[Union[int, str]] = None,

        # sar
        acceleration: Optional[Union[float, str]] = None,
        maximum: Optional[Union[float, str]] = None,

        # beta
        code2: Optional[str] = None,

        # token
        api_token: Optional[str] = None,
    ) -> str:
        """
        Technical Indicators API (spec-aligned)

        Notes:
          - Each request consumes 5 API calls (Marketplace accounting).
          - Supports all documented functions (sma, ema, wma, macd, rsi, stochastic, stochrsi, dmi/dx, adx, atr, cci, sar, beta, bbands, volatility, avgvol, avgvolccy, splitadjusted, format_amibroker).

        Args mirror API docs; only provided params are passed through.
        """
        # --- Required/typed validation ---
        if not ticker or not isinstance(ticker, str):
            return _err("Parameter 'ticker' is required and must be a string (e.g., 'AAPL.US').")

        fn = _normalize_function(function)
        if not fn:
            return _err(
                "Invalid 'function'. Allowed: "
                + ", ".join(sorted(ALLOWED_FUNCTIONS | set(FUNC_ALIASES.keys())))
            )

        if order not in ALLOWED_ORDER:
            return _err(f"Invalid 'order'. Allowed values: {sorted(ALLOWED_ORDER)}")

        if fmt not in ALLOWED_FMT:
            return _err(f"Invalid 'fmt'. Allowed values: {sorted(ALLOWED_FMT)}")

        if start_date is not None and not _valid_date(start_date):
            return _err("Parameter 'start_date' must be YYYY-MM-DD when provided.")
        if end_date is not None and not _valid_date(end_date):
            return _err("Parameter 'end_date' must be YYYY-MM-DD when provided.")
        if start_date and end_date:
            if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
                return _err("'start_date' cannot be after 'end_date'.")

        if filter and fmt != "json":
            return _err("Parameter 'filter' works only with fmt='json'.")

        # period-like ints
        for name, val in [
            ("period", period),
            ("fast_kperiod", fast_kperiod),
            ("slow_kperiod", slow_kperiod),
            ("slow_dperiod", slow_dperiod),
            ("fast_dperiod", fast_dperiod),
            ("fast_period", fast_period),
            ("slow_period", slow_period),
            ("signal_period", signal_period),
        ]:
            msg = _validate_period(name, val)
            if msg:
                return _err(msg)

        # floats for SAR
        for name, val in [
            ("acceleration", acceleration),
            ("maximum", maximum),
        ]:
            msg = _validate_float(name, val)
            if msg:
                return _err(msg)

        # agg_period for splitadjusted only
        if agg_period is not None:
            if fn != "splitadjusted":
                return _err("Parameter 'agg_period' is only valid when function='splitadjusted'.")
            if agg_period not in ALLOWED_AGG_PERIOD:
                return _err(f"Invalid 'agg_period'. Allowed: {sorted(ALLOWED_AGG_PERIOD)}")

        # splitadjusted_only supported subset (we pass through if provided for others, but validate type)
        if splitadjusted_only is not None:
            # normalize to 0/1 string
            if isinstance(splitadjusted_only, bool):
                splitadjusted_only = "1" if splitadjusted_only else "0"
            else:
                sval = str(splitadjusted_only).strip()
                if sval not in {"0", "1"}:
                    return _err("Parameter 'splitadjusted_only' must be 0/1, true/false.")
                splitadjusted_only = sval
            # (Optional strictness) warn if function not in supported set — we'll just allow pass-through.

        # --- Build URL ---
        # Base: /api/technical/{ticker}
        url = f"{EODHD_API_BASE}/technical/{ticker}?function={fn}&order={order}&fmt={fmt}"

        if start_date:
            url += f"&from={start_date}"
        if end_date:
            url += f"&to={end_date}"
        if filter:
            url += f"&filter={filter}"
        if period is not None:
            url += f"&period={int(period)}"

        # function-specific extras
        if fn == "splitadjusted":
            if agg_period:
                url += f"&agg_period={agg_period}"

        if fn == "stochastic":
            if fast_kperiod is not None:
                url += f"&fast_kperiod={int(fast_kperiod)}"
            if slow_kperiod is not None:
                url += f"&slow_kperiod={int(slow_kperiod)}"
            if slow_dperiod is not None:
                url += f"&slow_dperiod={int(slow_dperiod)}"

        if fn == "stochrsi":
            if fast_kperiod is not None:
                url += f"&fast_kperiod={int(fast_kperiod)}"
            if fast_dperiod is not None:
                url += f"&fast_dperiod={int(fast_dperiod)}"

        if fn == "macd":
            if fast_period is not None:
                url += f"&fast_period={int(fast_period)}"
            if slow_period is not None:
                url += f"&slow_period={int(slow_period)}"
            if signal_period is not None:
                url += f"&signal_period={int(signal_period)}"

        if fn == "sar":
            if acceleration is not None:
                url += f"&acceleration={float(acceleration)}"
            if maximum is not None:
                url += f"&maximum={float(maximum)}"

        if fn == "beta":
            if code2:
                url += f"&code2={code2}"

        # splitadjusted_only (works with several functions)
        if splitadjusted_only is not None:
            url += f"&splitadjusted_only={splitadjusted_only}"

        if api_token:
            url += f"&api_token={api_token}"

        # --- Execute request ---
        data = await make_request(url)

        # --- Normalize/return ---
        if data is None:
            return _err("No response from API.")

        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            return json.dumps(data, indent=2)
        except Exception:
            if isinstance(data, str):
                # For CSV (if make_request is updated to return text)
                return json.dumps({"csv": data}, indent=2)
            return _err("Unexpected response format from API.")
