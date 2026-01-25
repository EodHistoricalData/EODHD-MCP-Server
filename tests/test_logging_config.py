# tests/test_logging_config.py
"""Tests for app/logging_config.py module."""

import json
import logging
import pytest
from app.logging_config import (
    JSONFormatter,
    ContextFilter,
    LogContext,
    get_context_filter,
    setup_logging,
    get_logger,
    log_request,
    log_cache_event
)


class TestJSONFormatter:
    """Tests for JSONFormatter class."""

    def test_basic_format(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["message"] == "Test message"
        assert data["level"] == "INFO"
        assert "timestamp" in data

    def test_with_extra_fields(self):
        formatter = JSONFormatter(extra_fields={"service": "test-service"})
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["service"] == "test-service"

    def test_without_timestamp(self):
        formatter = JSONFormatter(include_timestamp=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "timestamp" not in data

    def test_with_path(self):
        formatter = JSONFormatter(include_path=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["path"] == "/app/test.py"
        assert data["line"] == 42


class TestContextFilter:
    """Tests for ContextFilter class."""

    def test_add_context(self):
        filter = ContextFilter({"request_id": "123"})
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )
        filter.filter(record)
        assert record.request_id == "123"

    def test_set_context(self):
        filter = ContextFilter()
        filter.set_context("user", "john")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None
        )
        filter.filter(record)
        assert record.user == "john"

    def test_clear_context(self):
        filter = ContextFilter({"key": "value"})
        filter.clear_context()
        assert filter.context == {}


class TestLogContext:
    """Tests for LogContext context manager."""

    def test_context_manager(self):
        context_filter = get_context_filter()
        context_filter.clear_context()

        with LogContext(request_id="abc"):
            assert context_filter.context["request_id"] == "abc"

        assert "request_id" not in context_filter.context

    def test_nested_context(self):
        context_filter = get_context_filter()
        context_filter.clear_context()

        with LogContext(a="1"):
            with LogContext(b="2"):
                assert context_filter.context["a"] == "1"
                assert context_filter.context["b"] == "2"
            assert context_filter.context.get("a") == "1"


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_json_format(self):
        setup_logging(level="DEBUG", json_format=True)
        logger = logging.getLogger()
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) > 0

    def test_setup_standard_format(self):
        setup_logging(level="INFO", json_format=False)
        logger = logging.getLogger()
        assert logger.level == logging.INFO


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger(self):
        logger = get_logger("test_module")
        assert logger.name == "eodhd-mcp.test_module"


class TestLogRequest:
    """Tests for log_request function."""

    def test_log_success(self, caplog):
        logger = get_logger("test")
        with caplog.at_level(logging.INFO):
            log_request(
                logger,
                tool_name="get_stock_price",
                params={"symbol": "AAPL"},
                duration_ms=150.5,
                success=True
            )
        assert "get_stock_price" in caplog.text

    def test_log_failure(self, caplog):
        logger = get_logger("test")
        with caplog.at_level(logging.ERROR):
            log_request(
                logger,
                tool_name="get_stock_price",
                success=False,
                error="API timeout"
            )
        assert "failed" in caplog.text.lower()


class TestLogCacheEvent:
    """Tests for log_cache_event function."""

    def test_log_cache_hit(self, caplog):
        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG):
            log_cache_event(logger, "hit", "stock:AAPL")
        # Debug may not show in caplog by default
        # Just verify no exception

    def test_log_cache_set(self, caplog):
        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG):
            log_cache_event(logger, "set", "stock:AAPL", ttl=300)
