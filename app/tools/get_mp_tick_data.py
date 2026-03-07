#get_mp_tick_data.py

import json
from typing import Optional, Union

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def _to_int(name: str, v: Union[int, str, None]) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.isdigit():
        return int(v)
    raise ValueError(f"'{name}' must be an integer UNIX timestamp in seconds (UTC).")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_tick_data(
        ticker: str,                                # maps to s=, e.g. "AAPL"
        from_timestamp: Optional[Union[int, str]] = None,   # UNIX seconds (UTC)
        to_timestamp: Optional[Union[int, str]] = None,     # UNIX seconds (UTC)
        limit: Optional[Union[int, str]] = None,            # 1-10000
        api_token: Optional[str] = None,                    # per-call override
    ) -> str:
        """
        [Marketplace] Fetch individual trade ticks (tick-by-tick data) for US stocks. Use when
        asked about granular trade-level data, tick history, or microstructure analysis.
        Returns timestamp (ms), price, shares, market center, and sequence for each trade.
        Covers US equities only. Time range defaults to yesterday if not specified.
        This is the paid Marketplace tick data provider. For free-tier tick data, use get_us_tick_data.
        Consumes 10 API calls per request.

        Args:
            ticker (str): Ticker symbol, max 30 chars (e.g. 'AAPL', 'MSFT').
            from_timestamp (int, optional): Start UNIX time in seconds. Default: yesterday start.
            to_timestamp (int, optional): End UNIX time in seconds. Default: yesterday end.
            limit (int, optional): Max ticks to return (1-10000). Default: all in range.
            api_token (str, optional): Per-call token override; env token used otherwise.
        """
        if not ticker or not isinstance(ticker, str):
            raise ToolError("Parameter 'ticker' is required (e.g. 'AAPL').")

        ticker = ticker.strip()
        if len(ticker) > 30:
            raise ToolError("Parameter 'ticker' must be at most 30 characters.")

        url = f"{EODHD_API_BASE}/mp/unicornbay/tickdata/ticks?s={ticker}"

        if from_timestamp is not None:
            try:
                f_ts = _to_int("from_timestamp", from_timestamp)
            except ValueError as ve:
                raise ToolError(str(ve))
            if f_ts is not None and f_ts < 0:
                raise ToolError("'from_timestamp' must be a non-negative UNIX timestamp.")
            url += f"&from={f_ts}"

        if to_timestamp is not None:
            try:
                t_ts = _to_int("to_timestamp", to_timestamp)
            except ValueError as ve:
                raise ToolError(str(ve))
            if t_ts is not None and t_ts < 0:
                raise ToolError("'to_timestamp' must be a non-negative UNIX timestamp.")
            url += f"&to={t_ts}"

        if limit is not None:
            try:
                lim = int(limit)
            except (ValueError, TypeError):
                raise ToolError("Parameter 'limit' must be an integer (1-10000).")
            if lim < 1 or lim > 10000:
                raise ToolError("Parameter 'limit' must be between 1 and 10000.")
            url += f"&limit={lim}"

        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            raise ToolError("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            raise ToolError(str(data["error"]))

        try:
            return json.dumps(data, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
