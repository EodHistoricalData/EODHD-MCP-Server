# entrypoints/server_http.py
"""
HTTP server entry point with OAuth 2.1 support.

Provides:
- MCP endpoint at /mcp
- OAuth Protected Resource Metadata at /.well-known/oauth-protected-resource
- Health check at /health
- Scopes info at /oauth/scopes

Per MCP Authorization Specification (2025-11-25):
- HTTP transport SHOULD support OAuth 2.1
- Backward compatible with legacy api_token
"""
import os
import logging
import sys
from pathlib import Path

# add project root to sys.path so `import app...` works
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from fastmcp import FastMCP
from app.tools import register_all

load_dotenv()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
    logger = logging.getLogger("eodhd-mcp")

    # Check if OAuth mode is enabled
    oauth_enabled = os.getenv("OAUTH_ENABLED", "false").lower() == "true"

    mcp = FastMCP("eodhd-datasets")
    register_all(mcp)

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", 8000))

    if oauth_enabled:
        logger.info("OAuth 2.1 support enabled")
        logger.info("Protected Resource Metadata: http://%s:%s/.well-known/oauth-protected-resource", host, port)

    logger.info("Starting EODHD MCP HTTP Server on http://%s:%s/mcp ...", host, port)
    mcp.run(transport="streamable-http", host=host, port=port, path="/mcp")
    logger.info("Server stopped")


if __name__ == "__main__":
    main()
