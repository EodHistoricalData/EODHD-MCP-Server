# app/tools/get_technical_indicators.py
import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url, coerce_date_param, sanitize_ticker, validate_date_range
from app.response_formatter import ResourceResponse, format_json_response, format_text_response, raise_on_api_error

logger = logging.getLogger(__name__)

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
    ) -> ResourceResponse:
        """

        Compute technical indicators for any ticker over a date range.
        Supported indicators: SMA, EMA, WMA, MACD, RSI, Stochastic, StochRSI, DMI/ADX, ATR,
        CCI, Parabolic SAR, Beta, Bollinger Bands, Volatility, Average Volume, and split-adjusted prices.
        Each indicator has configurable periods, and results include a time series of computed values.
        Consumes 5 API calls per request.
        For raw OHLCV price data, use get_historical_stock_prices instead.
        For fundamental analysis, use get_fundamentals_data instead.

        Returns:
            Array of objects, each with 'date' (str, YYYY-MM-DD) plus indicator-specific fields:
            - sma/ema/wma: {sma|ema|wma} (float)
            - rsi: {rsi} (float, 0-100)
            - macd: {macd, macd_signal, macd_hist} (float)
            - stochastic: {slow_k, slow_d} (float)
            - stochrsi: {stochrsi} (float)
            - bbands: {uband, mband, lband} (float — upper/middle/lower)
            - atr: {atr} (float)
            - adx: {adx} (float)
            - dmi: {dmi} (float)
            - cci: {cci} (float)
            - sar: {sar} (float)
            - beta: {beta} (float)
            - volatility: {volatility} (float)
            - avgvol: {avgvol} (int)
            - avgvolccy: {avgvolccy} (float — volume * close)
            - splitadjusted: {open, high, low, close, volume} (split-adjusted OHLCV)
            - stddev: {stddev} (float)
            - slope: {slope} (float)

            If filter is set (e.g. 'last_sma'), returns a single scalar value.

        Examples:
            "50-day SMA for Apple in 2025" → ticker="AAPL.US", function="sma", period=50, start_date="2025-01-01", end_date="2025-12-31"
            "RSI(14) for Bitcoin last 3 months" → ticker="BTC-USD.CC", function="rsi", period=14, start_date="2025-12-06"
            "MACD for Siemens with custom periods" → ticker="SIE.XETRA", function="macd", fast_period=12, slow_period=26, signal_period=9

        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL.US, MSFT.US, TSLA.US (stocks), VTI.US (ETF), SWPPX.US (mutual funds),
            EURUSD.FOREX, and BTC-USD.CC in all relevant APIs.
        """
        # --- Required/typed validation ---
        ticker = sanitize_ticker(ticker)

        fn = _normalize_function(function)
        if not fn:
            raise ToolError(
                "Invalid 'function'. Allowed: " + ", ".join(sorted(ALLOWED_FUNCTIONS | set(FUNC_ALIASES.keys())))
            )

        if order not in ALLOWED_ORDER:
            raise ToolError(f"Invalid 'order'. Allowed values: {sorted(ALLOWED_ORDER)}")

        if fmt not in ALLOWED_FMT:
            raise ToolError(f"Invalid 'fmt'. Allowed values: {sorted(ALLOWED_FMT)}")

        start_date = coerce_date_param(start_date, "start_date")
        end_date = coerce_date_param(end_date, "end_date")
        validate_date_range(start_date, end_date)

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
        for name, val in [  # type: ignore[assignment]
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
        params: dict = {
            "function": fn,
            "order": order,
            "fmt": fmt,
            "from": start_date,
            "to": end_date,
            "filter": filter,
            "period": int(period) if period is not None else None,
            "splitadjusted_only": splitadjusted_only,
            "api_token": api_token,
        }
        # function-specific extras
        if fn == "splitadjusted":
            params["agg_period"] = agg_period
        if fn in {"stochastic", "stochrsi"}:
            params["fast_kperiod"] = int(fast_kperiod) if fast_kperiod is not None else None
        if fn == "stochastic":
            params["slow_kperiod"] = int(slow_kperiod) if slow_kperiod is not None else None
            params["slow_dperiod"] = int(slow_dperiod) if slow_dperiod is not None else None
        if fn == "stochrsi":
            params["fast_dperiod"] = int(fast_dperiod) if fast_dperiod is not None else None
        if fn == "macd":
            params["fast_period"] = int(fast_period) if fast_period is not None else None
            params["slow_period"] = int(slow_period) if slow_period is not None else None
            params["signal_period"] = int(signal_period) if signal_period is not None else None
        if fn == "sar":
            params["acceleration"] = float(acceleration) if acceleration is not None else None
            params["maximum"] = float(maximum) if maximum is not None else None
        if fn == "beta":
            params["code2"] = code2
        url = build_url(f"technical/{ticker}", params)

        # --- Execute request ---
        data = await make_request(url, response_mode="text" if fmt == "csv" else "json")
        raise_on_api_error(data)

        # --- Normalize/return ---

        if fmt == "csv":
            if not isinstance(data, str):
                raise ToolError("Unexpected CSV response format from API.")
            return format_text_response(data, "text/csv", resource_path=f"technical/{ticker}-{fn}.csv")

        return format_json_response(data)
