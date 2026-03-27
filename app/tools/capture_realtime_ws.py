# app/tools/capture_realtime_ws.py

import asyncio
import json
import logging
import socket
import time
from urllib.parse import urlparse

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.config import get_api_key
from app.input_formatter import sanitize_ticker
from app.response_formatter import ResourceResponse, format_json_response

# WebSocket runtime
try:
    import websockets
except Exception:  # pragma: no cover
    websockets = None  # type: ignore[assignment]  # We'll error nicely at runtime if unavailable.

logger = logging.getLogger(__name__)

WS_BASE = "wss://ws.eodhistoricaldata.com/ws"

# Safety cap: default max captured data size (50 MB).  Prevents unbounded memory
# growth when high-throughput feeds (e.g. US trades) run for long durations.
DEFAULT_MAX_DATA_BYTES = 50 * 1024 * 1024

# Internal websockets receive-queue depth.  ``None`` (the previous value) allowed
# the library to buffer an unlimited number of frames in memory.  1024 frames is
# generous for any realistic capture window while still bounding memory.
DEFAULT_MAX_QUEUE = 1024

FEED_ENDPOINTS = {
    "us_trades": "us",  # trades (price, conditions, etc.)
    "us_quotes": "us-quote",  # quotes (bid/ask)
    "forex": "forex",
    "crypto": "crypto",
}


def _symbols_to_str(symbols: str | list[str]) -> str:
    if isinstance(symbols, str):
        parts = [part.strip() for part in symbols.split(",")]
    else:
        parts = [str(symbol).strip() for symbol in symbols if symbol is not None]

    cleaned = [sanitize_ticker(part, param_name="symbols") for part in parts if part]
    return ",".join(cleaned)


def _format_connection_error(exc: Exception, uri: str, timeout_seconds: float) -> str:
    host = urlparse(uri).hostname or "unknown host"

    if isinstance(exc, asyncio.TimeoutError):
        return f"Timed out while establishing WebSocket connection to {host} after {timeout_seconds} seconds."

    if isinstance(exc, socket.gaierror):
        reason = exc.strerror or str(exc) or "address resolution failed"
        return f"Failed to resolve WebSocket host '{host}': {reason}."

    if isinstance(exc, ConnectionRefusedError):
        return f"WebSocket connection to {host} was refused."

    if isinstance(exc, OSError):
        reason = exc.strerror or str(exc) or exc.__class__.__name__
        return f"WebSocket network error while connecting to {host}: {reason}."

    reason = str(exc).strip() or exc.__class__.__name__
    return f"Failed to connect to WebSocket endpoint {host}: {reason}."


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
        max_data_bytes: int = DEFAULT_MAX_DATA_BYTES,
    ) -> ResourceResponse:
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
            max_data_bytes (int): Maximum total captured data size in bytes (default 50 MB).
                Capture stops early if this limit is reached to prevent unbounded memory use.

        Demo:
            To manual data structure, use the manual API key "demo" (documentation: https://eodhd.com/financial-apis/).
            The "demo" key works for AAPL, MSFT, TSLA (stocks), EURUSD, and BTC-USD in Websocket API.
        """
        if websockets is None:
            raise ToolError("The 'websockets' package is required. Install with: pip install websockets")

        if feed not in FEED_ENDPOINTS:
            raise ToolError(f"Invalid 'feed'. Allowed: {sorted(FEED_ENDPOINTS.keys())}")

        if not symbols:
            raise ToolError("Parameter 'symbols' is required (e.g., 'AAPL,MSFT' or ['AAPL','MSFT']).")

        if not isinstance(duration_seconds, int) or not (1 <= duration_seconds <= 600):
            raise ToolError("'duration_seconds' must be an integer between 1 and 600.")

        if not isinstance(max_data_bytes, int) or max_data_bytes < 1:
            raise ToolError("'max_data_bytes' must be a positive integer.")

        endpoint = FEED_ENDPOINTS[feed]
        sym_str = _symbols_to_str(symbols)
        sym_list = [s for s in sym_str.split(",") if s]
        if not sym_list:
            raise ToolError("Parameter 'symbols' is required (e.g., 'AAPL,MSFT' or ['AAPL','MSFT']).")

        # Build WS URL with token (resolve from env if not provided)
        token = api_token or get_api_key() or ""
        uri = f"{WS_BASE}/{endpoint}?api_token={token}"

        started_at = int(time.time() * 1000)
        messages: list[dict] = []

        data_bytes_used = 0
        truncated = False

        async def _recv_loop(ws, stop_time):
            nonlocal messages, data_bytes_used, truncated
            # Subscribe
            sub = {"action": "subscribe", "symbols": sym_str}
            await ws.send(json.dumps(sub))

            # Receive until time, count, or byte limit
            while True:
                now = time.time()
                if now >= stop_time:
                    break
                if max_messages is not None and len(messages) >= max_messages:
                    break
                if data_bytes_used >= max_data_bytes:
                    truncated = True
                    logger.warning(
                        "WebSocket capture stopped: max_data_bytes limit reached (%s bytes)",
                        max_data_bytes,
                    )
                    break
                timeout_left = max(0.05, min(1.0, stop_time - now))
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=timeout_left)
                except TimeoutError:
                    continue  # loop to check time again
                except Exception:
                    break
                msg_size = len(msg) if isinstance(msg, (str, bytes)) else 0
                data_bytes_used += msg_size
                try:
                    messages.append(json.loads(msg))
                except Exception:
                    messages.append({"raw": msg})

        try:
            ws = await websockets.connect(
                uri,
                open_timeout=connect_timeout,
                ping_interval=ping_interval,
                ping_timeout=ping_timeout,
                close_timeout=5,
                max_queue=DEFAULT_MAX_QUEUE,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise ToolError(_format_connection_error(e, uri, connect_timeout)) from e

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
            "data_bytes": data_bytes_used,
            "truncated": truncated,
            "messages": messages,
        }
        return format_json_response(result)
