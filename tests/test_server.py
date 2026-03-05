from server import build_parser

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
