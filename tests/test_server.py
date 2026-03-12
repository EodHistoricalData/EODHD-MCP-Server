import pytest
from server import _validate_oauth_secrets, build_parser


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


class TestValidateOAuthSecrets:
    """R5-CR-7: JWT_SECRET/SESSION_SECRET must not be weak when OAuth is on."""

    def test_no_abort_when_oauth_disabled(self, monkeypatch):
        monkeypatch.setenv("OAUTH_ENABLED", "false")
        monkeypatch.setenv("JWT_SECRET", "")
        monkeypatch.setenv("SESSION_SECRET", "")
        _validate_oauth_secrets()  # should not raise

    def test_abort_on_empty_jwt_secret(self, monkeypatch):
        monkeypatch.setenv("OAUTH_ENABLED", "true")
        monkeypatch.setenv("JWT_SECRET", "")
        monkeypatch.setenv("SESSION_SECRET", "real_secret_value_here_1234")
        with pytest.raises(SystemExit):
            _validate_oauth_secrets()

    def test_abort_on_placeholder_session_secret(self, monkeypatch):
        monkeypatch.setenv("OAUTH_ENABLED", "true")
        monkeypatch.setenv("JWT_SECRET", "real_secret_value_here_1234")
        monkeypatch.setenv("SESSION_SECRET", "change_this_secret_in_production")
        with pytest.raises(SystemExit):
            _validate_oauth_secrets()

    def test_passes_with_strong_secrets(self, monkeypatch):
        monkeypatch.setenv("OAUTH_ENABLED", "true")
        monkeypatch.setenv("JWT_SECRET", "kN3xR7vZ2qW9mP5sL8aF1dG6hJ4cB0t")
        monkeypatch.setenv("SESSION_SECRET", "yT6uI3oP8wE1rQ4aS7dF0gH2jK5lZ9x")
        _validate_oauth_secrets()  # should not raise
