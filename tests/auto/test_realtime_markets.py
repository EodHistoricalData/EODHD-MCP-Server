"""The real-time surface: every served market, and the minute-bar endpoint."""

import pytest

from app.tools.capture_realtime_ws import FEED_ENDPOINTS
from app.tools.get_realtime_minute_bars import REALTIME_HOST, VALID_MARKETS


def test_every_served_market_is_mapped():
    """The service serves ten markets; this tool used to know four.

    The Cboe equity markets each expose four streams — trades, quotes, one-minute bars and
    trading status — and forex and crypto have trades only.
    """
    assert FEED_ENDPOINTS == {
        "us_trades": "us",
        "us_quotes": "us-quote",
        "us_candles": "us-candles",
        "us_status": "us-status",
        "eu_trades": "eu",
        "eu_quotes": "eu-quote",
        "eu_candles": "eu-candles",
        "eu_status": "eu-status",
        "forex": "forex",
        "crypto": "crypto",
    }


def test_feed_names_map_to_distinct_endpoints():
    assert len(set(FEED_ENDPOINTS.values())) == len(FEED_ENDPOINTS)


def test_minute_bars_only_offers_the_markets_that_keep_bars():
    """crypto and forex answer /history with an empty array, so offering them would mislead."""
    assert VALID_MARKETS == ("us", "eu")


def test_minute_bars_uses_the_realtime_host_not_the_rest_base():
    """/history is served by the streaming host, not by EODHD_API_BASE."""
    from app.config import EODHD_API_BASE

    assert REALTIME_HOST == "https://ws.eodhistoricaldata.com"
    assert not REALTIME_HOST.startswith(EODHD_API_BASE)


@pytest.mark.asyncio
async def test_minute_bars_rejects_a_market_without_bars(mcp_with_tools):
    """A market that keeps no bars must fail loudly rather than return a silent empty array."""
    from fastmcp.exceptions import ToolError

    from app.tools.get_realtime_minute_bars import register

    captured = {}

    class _Mcp:
        def tool(self, **_kwargs):
            def deco(fn):
                captured["fn"] = fn
                return fn

            return deco

    register(_Mcp())
    with pytest.raises(ToolError) as exc:
        await captured["fn"](market="crypto", symbol="BTC-USD")
    assert "market" in str(exc.value)
