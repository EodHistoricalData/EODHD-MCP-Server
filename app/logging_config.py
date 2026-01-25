# app/logging_config.py
"""
JSON structured logging configuration for EODHD MCP Server.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Optional


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Outputs logs in JSON format for easy parsing by log aggregators.
    """

    def __init__(
        self,
        include_timestamp: bool = True,
        include_level: bool = True,
        include_logger: bool = True,
        include_path: bool = False,
        extra_fields: Optional[dict] = None
    ):
        super().__init__()
        self.include_timestamp = include_timestamp
        self.include_level = include_level
        self.include_logger = include_logger
        self.include_path = include_path
        self.extra_fields = extra_fields or {}

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data: dict[str, Any] = {}

        # Timestamp
        if self.include_timestamp:
            log_data["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Log level
        if self.include_level:
            log_data["level"] = record.levelname
            log_data["level_num"] = record.levelno

        # Logger name
        if self.include_logger:
            log_data["logger"] = record.name

        # Message
        log_data["message"] = record.getMessage()

        # File path and line number
        if self.include_path:
            log_data["path"] = record.pathname
            log_data["line"] = record.lineno
            log_data["function"] = record.funcName

        # Exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Extra fields from the record
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "taskName"
            ):
                log_data[key] = value

        # Static extra fields
        log_data.update(self.extra_fields)

        return json.dumps(log_data, default=str)


class ContextFilter(logging.Filter):
    """
    Filter that adds context information to log records.
    """

    def __init__(self, context: Optional[dict] = None):
        super().__init__()
        self.context = context or {}

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to the record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True

    def set_context(self, key: str, value: Any) -> None:
        """Set a context value."""
        self.context[key] = value

    def clear_context(self) -> None:
        """Clear all context values."""
        self.context.clear()


# Global context filter for request tracking
_context_filter = ContextFilter()


def get_context_filter() -> ContextFilter:
    """Get the global context filter."""
    return _context_filter


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    include_path: bool = False,
    extra_fields: Optional[dict] = None
) -> None:
    """
    Set up logging configuration for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON format (True) or standard format (False)
        include_path: Whether to include file path in logs
        extra_fields: Extra fields to include in every log message
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, level.upper()))

    if json_format:
        formatter = JSONFormatter(
            include_path=include_path,
            extra_fields=extra_fields or {"service": "eodhd-mcp"}
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(formatter)
    console_handler.addFilter(_context_filter)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (typically module name)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(f"eodhd-mcp.{name}")


class LogContext:
    """
    Context manager for adding temporary context to logs.

    Usage:
        with LogContext(request_id="123", user="john"):
            logger.info("Processing request")
    """

    def __init__(self, **kwargs: Any):
        self.context = kwargs
        self.previous_context: dict = {}

    def __enter__(self) -> "LogContext":
        """Save current context and add new values."""
        self.previous_context = _context_filter.context.copy()
        _context_filter.context.update(self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Restore previous context."""
        _context_filter.context = self.previous_context


def log_request(
    logger: logging.Logger,
    tool_name: str,
    params: Optional[dict] = None,
    duration_ms: Optional[float] = None,
    success: bool = True,
    error: Optional[str] = None
) -> None:
    """
    Log an API request with structured data.

    Args:
        logger: Logger instance
        tool_name: Name of the MCP tool
        params: Request parameters
        duration_ms: Request duration in milliseconds
        success: Whether the request was successful
        error: Error message if failed
    """
    extra = {
        "tool": tool_name,
        "success": success,
        "event_type": "api_request"
    }

    if params:
        # Sanitize params (remove sensitive data)
        safe_params = {k: v for k, v in params.items() if k != "api_token"}
        extra["params"] = safe_params

    if duration_ms is not None:
        extra["duration_ms"] = round(duration_ms, 2)

    if error:
        extra["error"] = error

    if success:
        logger.info(f"Tool {tool_name} completed", extra=extra)
    else:
        logger.error(f"Tool {tool_name} failed: {error}", extra=extra)


def log_cache_event(
    logger: logging.Logger,
    event: str,  # "hit", "miss", "set", "expire"
    key: str,
    ttl: Optional[int] = None
) -> None:
    """
    Log a cache event with structured data.

    Args:
        logger: Logger instance
        event: Cache event type
        key: Cache key
        ttl: Time to live (for set events)
    """
    extra = {
        "event_type": "cache",
        "cache_event": event,
        "cache_key": key
    }

    if ttl is not None:
        extra["ttl"] = ttl

    logger.debug(f"Cache {event}: {key}", extra=extra)
