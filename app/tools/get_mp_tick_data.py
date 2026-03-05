#get_mp_tick_data.py

import json
from typing import Optional, Union

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)


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
        Marketplace: US Stock Market Tick Data
        GET /api/mp/unicornbay/tickdata/ticks

        Returns granular trade ticks for US equities via the Marketplace tick data provider.

        Args:
            ticker (str): Ticker symbol, max 30 chars (e.g. 'AAPL', 'MSFT').
            from_timestamp (int, optional): Start UNIX time in seconds. Default: yesterday start.
            to_timestamp (int, optional): End UNIX time in seconds. Default: yesterday end.
            limit (int, optional): Max ticks to return (1-10000). Default: all in range.
            api_token (str, optional): Per-call token override; env token used otherwise.

        Notes:
            - Marketplace product: 10 API calls per request.
            - Columnar response format with fields: ts (milliseconds), price, shares,
              mkt, seq, sl, sub_mkt.
            - Timestamp params in seconds but response ts in milliseconds.
            - US stocks only.
        """
        if not ticker or not isinstance(ticker, str):
            return _err("Parameter 'ticker' is required (e.g. 'AAPL').")

        ticker = ticker.strip()
        if len(ticker) > 30:
            return _err("Parameter 'ticker' must be at most 30 characters.")

        url = f"{EODHD_API_BASE}/mp/unicornbay/tickdata/ticks?s={ticker}"

        if from_timestamp is not None:
            try:
                f_ts = _to_int("from_timestamp", from_timestamp)
            except ValueError as ve:
                return _err(str(ve))
            if f_ts is not None and f_ts < 0:
                return _err("'from_timestamp' must be a non-negative UNIX timestamp.")
            url += f"&from={f_ts}"

        if to_timestamp is not None:
            try:
                t_ts = _to_int("to_timestamp", to_timestamp)
            except ValueError as ve:
                return _err(str(ve))
            if t_ts is not None and t_ts < 0:
                return _err("'to_timestamp' must be a non-negative UNIX timestamp.")
            url += f"&to={t_ts}"

        if limit is not None:
            try:
                lim = int(limit)
            except (ValueError, TypeError):
                return _err("Parameter 'limit' must be an integer (1-10000).")
            if lim < 1 or lim > 10000:
                return _err("Parameter 'limit' must be between 1 and 10000.")
            url += f"&limit={lim}"

        if api_token:
            url += f"&api_token={api_token}"

        data = await make_request(url)

        if data is None:
            return _err("No response from API.")
        if isinstance(data, dict) and data.get("error"):
            return json.dumps({"error": data["error"]}, indent=2)

        try:
            return json.dumps(data, indent=2)
        except Exception:
            return _err("Unexpected response format from API.")
