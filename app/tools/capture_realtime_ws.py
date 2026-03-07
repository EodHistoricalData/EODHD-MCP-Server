# capture_realtime_ws.py

import asyncio
import json
import time

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

# WebSocket runtime
try:
    import websockets
except Exception:  # pragma: no cover
    websockets = None  # We'll error nicely at runtime if unavailable.

WS_BASE = "wss://ws.eodhistoricaldata.com/ws"

FEED_ENDPOINTS = {
    "us_trades": "us",  # trades (price, conditions, etc.)
    "us_quotes": "us-quote",  # quotes (bid/ask)
    "forex": "forex",
    "crypto": "crypto",
}


def _symbols_to_str(symbols: str | list[str]) -> str:
    if isinstance(symbols, str):
        return symbols.replace(" ", "")
    return ",".join(s.strip() for s in symbols if s and str(s).strip())


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def capture_realtime_ws(
        feed: str,
        symbols: str | list[str],
        duration_seconds: int = 5,
        api_token: str | None = None,
        max_messages: int | None = None,
        ping_interval: float = 20.0,
        ping_timeout: float = 20.0,
        connect_timeout: float = 15.0,
    ) -> str:
        """

        Capture real-time streaming market data via WebSocket for a fixed time window. Use when
        the user needs live tick-by-tick prices, real-time trades, bid/ask quotes, or streaming
        forex/crypto rates.

        Connects to EODHD WebSocket feeds (us_trades, us_quotes, forex, crypto), subscribes to
        specified symbols, collects messages for the given duration, then returns all captured
        data at once. Unlike get_live_price_data (REST snapshot), this streams continuous updates.

        For a single REST-based price snapshot, use get_live_price_data instead.
        For historical tick-level trade data (not real-time), use get_us_tick_data.

        Args:
            feed (str): One of {'us_trades','us_quotes','forex','crypto'}.
            symbols (str | list[str]): Single or comma-separated symbols, or a list.
                Returns:
            Object with:
            - feed (str): feed name used
            - endpoint (str): WS endpoint path
            - symbols (array[str]): subscribed symbols
            - duration_seconds (int): capture window length
            - started_at (int): start epoch in ms
            - ended_at (int): end epoch in ms
            - message_count (int): total messages captured
            - messages (array): captured messages, each varies by feed:
              - us_trades: s (str, symbol), p (float, price), v (int, volume), t (int, timestamp ms), c (str, conditions)
              - us_quotes: s (str, symbol), ap (float, ask price), as (int, ask size), bp (float, bid price), bs (int, bid size), t (int, timestamp ms)
              - forex: s (str, symbol), a (float, ask), b (float, bid), t (int, timestamp ms)
              - crypto: s (str, symbol), p (float, price), q (float, quantity), t (int, timestamp ms)

        Examples: 'AAPL,MSFT,TSLA' (US), 'EURUSD' (forex), 'ETH-USD,BTC-USD' (crypto).
            duration_seconds (int): How long to capture messages (1..600). Default 5.
            api_token (str, optional): WebSocket token; 'demo' supports limited symbols.
            max_messages (int, optional): Stop early after N messages.
            ping_interval (float): WebSocket ping interval in seconds.
            ping_timeout (float): WebSocket ping timeout in seconds.
            connect_timeout (float): Overall connection timeout in seconds.
        
        """
        if websockets is None:
            raise ToolError("The 'websockets' package is required. Install with: pip install websockets")

        if feed not in FEED_ENDPOINTS:
            raise ToolError(f"Invalid 'feed'. Allowed: {sorted(FEED_ENDPOINTS.keys())}")

        if not symbols:
            raise ToolError("Parameter 'symbols' is required (e.g., 'AAPL,MSFT' or ['AAPL','MSFT']).")

        if not isinstance(duration_seconds, int) or not (1 <= duration_seconds <= 600):
            raise ToolError("'duration_seconds' must be an integer between 1 and 600.")

        endpoint = FEED_ENDPOINTS[feed]
        sym_str = _symbols_to_str(symbols)
        sym_list = [s for s in sym_str.split(",") if s]

        # Build WS URL with token
        token = api_token or "demo"
        uri = f"{WS_BASE}/{endpoint}?api_token={token}"

        started_at = int(time.time() * 1000)
        messages: list[dict] = []

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
                except TimeoutError:
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
            except TimeoutError:
                raise ToolError("Timed out while establishing WebSocket connection.")
        except Exception as e:
            raise ToolError(f"Failed to connect to WebSocket endpoint: {e!s}")

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
