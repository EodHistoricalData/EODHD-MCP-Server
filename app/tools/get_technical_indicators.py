# get_technical_indicators.py
import json
from datetime import datetime

from app.api_client import make_request
from app.config import EODHD_API_BASE
from app.validators import validate_date, validate_ticker
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

ALLOWED_ORDER = {"a", "d"}  # ascending, descending (per docs)
ALLOWED_FMT = {"json", "csv"}
ALLOWED_AGG_PERIOD = {"d", "w", "m"}  # for splitadjusted only
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
    "dmi",  # aka dx
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
    "sma",
    "ema",
    "wma",
    "volatility",
    "rsi",
    "slope",
    "macd",
}


def _normalize_function(fn: str) -> str | None:
    if not isinstance(fn, str) or not fn.strip():
        return None
    f = fn.strip().lower()
    f = FUNC_ALIASES.get(f, f)
    return f if f in ALLOWED_FUNCTIONS else None


def _validate_period(name: str, val: int | str | None) -> str | None:
    if val is None or val == "":
        return None
    try:
        ival = int(val)
    except Exception:
        return f"Parameter '{name}' must be an integer."
    if not (PERIOD_MIN <= ival <= PERIOD_MAX):
        return f"Parameter '{name}' out of range [{PERIOD_MIN}, {PERIOD_MAX}]."
    return None


def _validate_float(name: str, val: int | float | str | None) -> str | None:
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
        function: str,  # required (e.g., 'sma', 'macd', 'stochastic', ...)
        # common optional
        start_date: str | None = None,  # 'from' (YYYY-MM-DD)
        end_date: str | None = None,  # 'to'   (YYYY-MM-DD)
        order: str = "a",  # 'a' | 'd'
        fmt: str = "json",  # 'json' | 'csv'
        filter: str | None = None,  # e.g., 'last_ema', 'last_volume'
        splitadjusted_only: int | bool | str | None = None,  # 0/1 or bool (only for some functions)
        # shared indicator params
        period: int | str | None = None,
        # splitadjusted
        agg_period: str | None = None,  # 'd'|'w'|'m' (splitadjusted only)
        # stochastic
        fast_kperiod: int | str | None = None,
        slow_kperiod: int | str | None = None,
        slow_dperiod: int | str | None = None,
        # stochrsi
        fast_dperiod: int | str | None = None,
        # macd
        fast_period: int | str | None = None,
        slow_period: int | str | None = None,
        signal_period: int | str | None = None,
        # sar
        acceleration: float | str | None = None,
        maximum: float | str | None = None,
        # beta
        code2: str | None = None,
        # token
        api_token: str | None = None,
    ) -> str:
        """
        Technical Indicators API (spec-aligned)

        Notes:
          - Each request consumes 5 API calls (Marketplace accounting).
          - Supports all documented functions (sma, ema, wma, macd, rsi, stochastic, stochrsi, dmi/dx, adx, atr, cci, sar, beta, bbands, volatility, avgvol, avgvolccy, splitadjusted, format_amibroker).

        Args mirror API docs; only provided params are passed through.
        """
        # --- Required/typed validation ---
        ticker = validate_ticker(ticker)

        fn = _normalize_function(function)
        if not fn:
            raise ToolError(
                "Invalid 'function'. Allowed: " + ", ".join(sorted(ALLOWED_FUNCTIONS | set(FUNC_ALIASES.keys())))
            )

        if order not in ALLOWED_ORDER:
            raise ToolError(f"Invalid 'order'. Allowed values: {sorted(ALLOWED_ORDER)}")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed values: {sorted(ALLOWED_FMT)}")

        validate_date(start_date, "start_date")
        validate_date(end_date, "end_date")
        if start_date and end_date:
            if datetime.strptime(start_date, "%Y-%m-%d") > datetime.strptime(end_date, "%Y-%m-%d"):
                raise ToolError("'start_date' cannot be after 'end_date'.")

        if filter and fmt != "json":
            raise ToolError("Parameter 'filter' works only with fmt='json'.")

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
                raise ToolError(msg)

        # floats for SAR
        for name, val in [
            ("acceleration", acceleration),
            ("maximum", maximum),
        ]:
            msg = _validate_float(name, val)
            if msg:
                raise ToolError(msg)

        # agg_period for splitadjusted only
        if agg_period is not None:
            if fn != "splitadjusted":
                raise ToolError("Parameter 'agg_period' is only valid when function='splitadjusted'.")
            if agg_period not in ALLOWED_AGG_PERIOD:
                raise ToolError(f"Invalid 'agg_period'. Allowed: {sorted(ALLOWED_AGG_PERIOD)}")

        # splitadjusted_only supported subset (we pass through if provided for others, but validate type)
        if splitadjusted_only is not None:
            # normalize to 0/1 string
            if isinstance(splitadjusted_only, bool):
                splitadjusted_only = "1" if splitadjusted_only else "0"
            else:
                sval = str(splitadjusted_only).strip()
                if sval not in {"0", "1"}:
                    raise ToolError("Parameter 'splitadjusted_only' must be 0/1, true/false.")
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
            raise ToolError("No response from API.")

        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return json.dumps(data, indent=2)
        except Exception:
            if isinstance(data, str):
                # For CSV (if make_request is updated to return text)
                return json.dumps({"csv": data}, indent=2)
            raise ToolError("Unexpected response format from API.")
