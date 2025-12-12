#capture_realtime_ws.py

import asyncio
import json
import time
from typing import List, Optional, Union

from fastmcp import FastMCP
from mcp.types import ToolAnnotations


# WebSocket runtime
try:
    import websockets
except Exception as e:  # pragma: no cover
    websockets = None  # We'll error nicely at runtime if unavailable.

WS_BASE = "wss://ws.eodhistoricaldata.com/ws"

FEED_ENDPOINTS = {
    "us_trades": "us",         # trades (price, conditions, etc.)
    "us_quotes": "us-quote",   # quotes (bid/ask)
    "forex": "forex",
    "crypto": "crypto",
}

def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)

def _symbols_to_str(symbols: Union[str, List[str]]) -> str:
    if isinstance(symbols, str):
        return symbols.replace(" ", "")
    return ",".join(s.strip() for s in symbols if s and str(s).strip())

def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def capture_realtime_ws(
        feed: str,
        symbols: Union[str, List[str]],
        duration_seconds: int = 5,
        api_token: Optional[str] = None,
        max_messages: Optional[int] = None,
        ping_interval: float = 20.0,
        ping_timeout: float = 20.0,
        connect_timeout: float = 15.0,
    ) -> str:
        """
        Capture real-time data via WebSockets for a fixed window, then return it.

        Args:
            feed (str): One of {'us_trades','us_quotes','forex','crypto'}.
            symbols (str | list[str]): Single or comma-separated symbols, or a list.
                Examples:
                  - US trades/quotes: 'AAPL,MSFT,TSLA'
                  - FOREX: 'EURUSD'
                  - Crypto: 'ETH-USD,BTC-USD'
            duration_seconds (int): How long to capture messages (1..600). Default 5.
            api_token (str, optional): WebSocket token; 'demo' supports AAPL, MSFT, TSLA, EURUSD, ETH-USD, BTC-USD.
            max_messages (int, optional): Stop early after N messages.
            ping_interval (float): websockets.connect ping interval (seconds).
            ping_timeout (float): websockets.connect ping timeout (seconds).
            connect_timeout (float): Overall timeout to establish connection (seconds).

        Returns:
            str: JSON string with
                {
                  "feed": ...,
                  "endpoint": ...,
                  "symbols": [...],
                  "duration_seconds": ...,
                  "started_at": <epoch_ms>,
                  "ended_at": <epoch_ms>,
                  "message_count": N,
                  "messages": [ {parsed message dicts...} ]
                }
        """
        if websockets is None:
            return _err("The 'websockets' package is required. Install with: pip install websockets")

        if feed not in FEED_ENDPOINTS:
            return _err(f"Invalid 'feed'. Allowed: {sorted(FEED_ENDPOINTS.keys())}")

        if not symbols:
            return _err("Parameter 'symbols' is required (e.g., 'AAPL,MSFT' or ['AAPL','MSFT']).")

        if not isinstance(duration_seconds, int) or not (1 <= duration_seconds <= 600):
            return _err("'duration_seconds' must be an integer between 1 and 600.")

        endpoint = FEED_ENDPOINTS[feed]
        sym_str = _symbols_to_str(symbols)
        sym_list = [s for s in sym_str.split(",") if s]

        # Build WS URL with token
        token = api_token or "demo"
        uri = f"{WS_BASE}/{endpoint}?api_token={token}"

        started_at = int(time.time() * 1000)
        messages: List[dict] = []

        async def _recv_loop(ws, stop_time):
            nonlocal messages
            # Subscribe
            sub = {"action": "subscribe", "symbols": sym_str}
            await ws.send(json.dumps(sub))

            # Receive until time or count
            while True:
                now = time.time()
                if now >= stop_time:
                    break
                if max_messages is not None and len(messages) >= max_messages:
                    break
                timeout_left = max(0.05, min(1.0, stop_time - now))
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=timeout_left)
                except asyncio.TimeoutError:
                    continue  # loop to check time again
                except Exception:
                    break
                try:
                    messages.append(json.loads(msg))
                except Exception:
                    messages.append({"raw": msg})

        try:
            # Establish connection with overall timeout
            conn_task = websockets.connect(
                uri,
                ping_interval=ping_interval,
                ping_timeout=ping_timeout,
                close_timeout=5,
                max_queue=None,  # do not artificially limit
            )
            try:
                ws = await asyncio.wait_for(conn_task, timeout=connect_timeout)
            except asyncio.TimeoutError:
                return _err("Timed out while establishing WebSocket connection.")
        except Exception as e:
            return _err(f"Failed to connect to WebSocket endpoint: {str(e)}")

        try:
            stop_time = time.time() + duration_seconds
            await _recv_loop(ws, stop_time)
        finally:
            try:
                await ws.close()
            except Exception:
                pass

        ended_at = int(time.time() * 1000)

        result = {
            "feed": feed,
            "endpoint": endpoint,
            "symbols": sym_list,
            "duration_seconds": duration_seconds,
            "started_at": started_at,
            "ended_at": ended_at,
            "message_count": len(messages),
            "messages": messages,
        }
        return json.dumps(result, indent=2)
