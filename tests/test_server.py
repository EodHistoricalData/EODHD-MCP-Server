"""Tests for server.py — build_parser and main()."""

from unittest.mock import MagicMock, patch

from server import build_parser, main

# ---------------------------------------------------------------------------
# build_parser — existing tests
# ---------------------------------------------------------------------------


def test_default_args():
    parser = build_parser()
    args = parser.parse_args([])
    assert args.stdio is False
    assert args.sse is False
    assert args.port == 8000
    assert args.path == "/mcp"


def test_stdio_flag():
    parser = build_parser()
    args = parser.parse_args(["--stdio"])
    assert args.stdio is True
    assert args.sse is False


def test_sse_flag():
    parser = build_parser()
    args = parser.parse_args(["--sse"])
    assert args.sse is True
    assert args.stdio is False


def test_custom_port_and_host():
    parser = build_parser()
    args = parser.parse_args(["--host", "0.0.0.0", "--port", "9000"])
    assert args.host == "0.0.0.0"
    assert args.port == 9000


def test_apikey_flag():
    parser = build_parser()
    args = parser.parse_args(["--apikey", "mykey123"])
    assert args.api_key == "mykey123"


def test_api_key_alias():
    """--api-key is an alias for --apikey."""
    parser = build_parser()
    args = parser.parse_args(["--api-key", "mykey456"])
    assert args.api_key == "mykey456"


def test_http_flag():
    parser = build_parser()
    args = parser.parse_args(["--http"])
    assert args.http is True
    assert args.stdio is False
    assert args.sse is False


def test_log_level_flag():
    parser = build_parser()
    args = parser.parse_args(["--log-level", "DEBUG"])
    assert args.log_level == "DEBUG"


# ---------------------------------------------------------------------------
# main() — transport dispatch (TST-9)
# close_client is imported inside finally block, so we patch at
# app.api_client.close_client instead of server.close_client
# ---------------------------------------------------------------------------


class TestMain:
    def _mock_mcp(self):
        """Create a mock FastMCP that records run() calls."""
        mock = MagicMock()
        mock.run = MagicMock()
        return mock

    @patch("app.api_client.close_client")
    @patch("server.FastMCP")
    @patch("server.register_all_tools")
    @patch("server.register_all_resources")
    @patch("server.register_all_prompts")
    @patch("server.load_dotenv")
    def test_stdio_transport(self, _dotenv, _prompts, _resources, _tools, mock_fastmcp, _close):
        mock_mcp = self._mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        result = main(["--stdio"])
        assert result == 0
        mock_mcp.run.assert_called_once_with(transport="stdio")

    @patch("app.api_client.close_client")
    @patch("server.FastMCP")
    @patch("server.register_all_tools")
    @patch("server.register_all_resources")
    @patch("server.register_all_prompts")
    @patch("server.load_dotenv")
    def test_sse_transport(self, _dotenv, _prompts, _resources, _tools, mock_fastmcp, _close):
        mock_mcp = self._mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        result = main(["--sse"])
        assert result == 0
        mock_mcp.run.assert_called_once()
        call_kwargs = mock_mcp.run.call_args[1]
        assert call_kwargs["transport"] == "sse"

    @patch("app.api_client.close_client")
    @patch("server.FastMCP")
    @patch("server.register_all_tools")
    @patch("server.register_all_resources")
    @patch("server.register_all_prompts")
    @patch("server.load_dotenv")
    def test_default_http_transport(self, _dotenv, _prompts, _resources, _tools, mock_fastmcp, _close):
        mock_mcp = self._mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        result = main([])
        assert result == 0
        mock_mcp.run.assert_called_once()
        call_kwargs = mock_mcp.run.call_args[1]
        assert call_kwargs["transport"] == "streamable-http"
        assert call_kwargs["port"] == 8000

    @patch("app.api_client.close_client")
    @patch("server.FastMCP")
    @patch("server.register_all_tools")
    @patch("server.register_all_resources")
    @patch("server.register_all_prompts")
    @patch("server.load_dotenv")
    def test_apikey_injects_env(self, _dotenv, _prompts, _resources, _tools, mock_fastmcp, _close, monkeypatch):
        mock_mcp = self._mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        monkeypatch.delenv("EODHD_API_KEY", raising=False)
        result = main(["--stdio", "--apikey", "injected_key"])
        assert result == 0
        import os

        assert os.environ.get("EODHD_API_KEY") == "injected_key"
        # restore
        monkeypatch.setenv("EODHD_API_KEY", "test_key_for_ci")

    @patch("app.api_client.close_client")
    @patch("server.FastMCP")
    @patch("server.register_all_tools")
    @patch("server.register_all_resources")
    @patch("server.register_all_prompts")
    @patch("server.load_dotenv")
    def test_keyboard_interrupt_returns_0(self, _dotenv, _prompts, _resources, _tools, mock_fastmcp, _close):
        mock_mcp = self._mock_mcp()
        mock_mcp.run.side_effect = KeyboardInterrupt
        mock_fastmcp.return_value = mock_mcp
        result = main(["--stdio"])
        assert result == 0

    @patch("app.api_client.close_client")
    @patch("server.FastMCP")
    @patch("server.register_all_tools")
    @patch("server.register_all_resources")
    @patch("server.register_all_prompts")
    @patch("server.load_dotenv")
    def test_exception_returns_1(self, _dotenv, _prompts, _resources, _tools, mock_fastmcp, _close):
        mock_mcp = self._mock_mcp()
        mock_mcp.run.side_effect = RuntimeError("boom")
        mock_fastmcp.return_value = mock_mcp
        result = main(["--stdio"])
        assert result == 1

    @patch("app.api_client.close_client")
    @patch("server.FastMCP")
    @patch("server.register_all_tools")
    @patch("server.register_all_resources")
    @patch("server.register_all_prompts")
    @patch("server.load_dotenv")
    def test_custom_port_and_path(self, _dotenv, _prompts, _resources, _tools, mock_fastmcp, _close):
        mock_mcp = self._mock_mcp()
        mock_fastmcp.return_value = mock_mcp
        result = main(["--port", "9000", "--path", "/api"])
        assert result == 0
        call_kwargs = mock_mcp.run.call_args[1]
        assert call_kwargs["port"] == 9000
        assert call_kwargs["path"] == "/api"
