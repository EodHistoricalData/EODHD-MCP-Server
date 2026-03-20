"""Tests for app.prompts — registration, templates, safe-register error handling."""

import logging
import types

from app.prompts import PROMPTS, _dedupe, _safe_register, register_all
from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# _dedupe
# ---------------------------------------------------------------------------


class TestDedupe:
    def test_removes_duplicates(self):
        assert _dedupe(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]

    def test_preserves_order(self):
        assert _dedupe(["c", "b", "a"]) == ["c", "b", "a"]

    def test_empty(self):
        assert _dedupe([]) == []


# ---------------------------------------------------------------------------
# _safe_register — error handling
# ---------------------------------------------------------------------------


class TestSafeRegister:
    def test_missing_module_logs_warning(self, caplog):
        mcp = FastMCP("test")
        with caplog.at_level(logging.WARNING):
            _safe_register(mcp, "nonexistent_module_xyz")
        assert "module not found" in caplog.text

    def test_module_without_register_logs_warning(self, caplog):
        mcp = FastMCP("test")
        with caplog.at_level(logging.WARNING):
            _safe_register(mcp, "analyze_stock", attr="no_such_func")
        assert "no callable" in caplog.text

    def test_register_that_raises_logs_error(self, caplog, monkeypatch):
        mcp = FastMCP("test")
        bad_mod = types.ModuleType("bad")
        bad_mod.register = lambda _mcp: 1 / 0

        monkeypatch.setattr(
            "app.prompts.importlib.import_module",
            lambda name, package=None: bad_mod,
        )
        with caplog.at_level(logging.ERROR):
            _safe_register(mcp, "bad")
        assert "Failed to register" in caplog.text

    def test_import_generic_exception_logs_error(self, caplog, monkeypatch):
        mcp = FastMCP("test")

        def _raise(*_a, **_kw):
            raise RuntimeError("boom")

        monkeypatch.setattr("app.prompts.importlib.import_module", _raise)
        with caplog.at_level(logging.ERROR):
            _safe_register(mcp, "broken")
        assert "Error importing" in caplog.text


# ---------------------------------------------------------------------------
# register_all
# ---------------------------------------------------------------------------


class TestRegisterAll:
    def test_registers_without_errors(self):
        mcp = FastMCP("test")
        register_all(mcp)

    def test_prompts_list_not_empty(self):
        assert len(PROMPTS) >= 3


# ---------------------------------------------------------------------------
# Prompt templates — content
# ---------------------------------------------------------------------------


def _render_text(mcp: FastMCP, name: str, arguments: dict | None = None) -> str:
    """Render a prompt and return the first message text."""
    import asyncio

    result = asyncio.run(mcp.render_prompt(name, arguments=arguments or {}))
    return result.messages[0].content.text


class TestAnalyzeStockPrompt:
    def setup_method(self):
        self.mcp = FastMCP("test")
        from app.prompts.analyze_stock import register

        register(self.mcp)

    def test_contains_ticker(self):
        text = _render_text(self.mcp, "analyze_stock", {"ticker": "AAPL.US"})
        assert "AAPL.US" in text

    def test_references_required_tools(self):
        text = _render_text(self.mcp, "analyze_stock", {"ticker": "TSLA.US"})
        assert "get_fundamentals_data" in text
        assert "get_historical_stock_prices" in text
        assert "get_technical_indicators" in text
        assert "get_company_news" in text

    def test_mentions_resolve_ticker(self):
        text = _render_text(self.mcp, "analyze_stock", {"ticker": "Apple"})
        assert "resolve_ticker" in text


class TestCompareStocksPrompt:
    def setup_method(self):
        self.mcp = FastMCP("test")
        from app.prompts.compare_stocks import register

        register(self.mcp)

    def test_contains_both_tickers(self):
        text = _render_text(self.mcp, "compare_stocks", {"ticker1": "AAPL.US", "ticker2": "MSFT.US"})
        assert "AAPL.US" in text
        assert "MSFT.US" in text

    def test_comparison_table_headers(self):
        text = _render_text(self.mcp, "compare_stocks", {"ticker1": "AAPL.US", "ticker2": "MSFT.US"})
        assert "P/E Ratio" in text
        assert "Market Cap" in text


class TestMarketOverviewPrompt:
    def setup_method(self):
        self.mcp = FastMCP("test")
        from app.prompts.market_overview import register

        register(self.mcp)

    def test_default_exchange(self):
        text = _render_text(self.mcp, "market_overview")
        assert "US" in text

    def test_custom_exchange(self):
        text = _render_text(self.mcp, "market_overview", {"exchange": "LSE"})
        assert "LSE" in text

    def test_references_required_tools(self):
        text = _render_text(self.mcp, "market_overview")
        assert "get_stock_screener_data" in text
        assert "get_economic_events" in text
        assert "get_upcoming_earnings" in text
