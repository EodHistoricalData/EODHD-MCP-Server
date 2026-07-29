# entrypoints/server_http.py
import asyncio
import logging
import os
import sys
from pathlib import Path

# add project root to sys.path so `import app...` works
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api_client import install_token_redaction
from app.prompts import register_all as register_all_prompts
from app.resources import register_all as register_all_resources
from app.tools import register_all as register_all_tools
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()


def main() -> None:
    mcp = FastMCP("eodhd-datasets")
    register_all_tools(mcp)
    register_all_resources(mcp)
    register_all_prompts(mcp)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
    install_token_redaction()
    logger = logging.getLogger("eodhd-mcp")
    logger.info("Starting EODHD MCP HTTP Server...")
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8000"))
    try:
        mcp.run(transport="streamable-http", host=host, port=port, path="/mcp")
    except (KeyboardInterrupt, asyncio.CancelledError):
        # anyio delivers SIGINT as a CancelledError, which is a BaseException: without
        # this the entry point exits with a traceback and code 1 on a normal Ctrl+C.
        logger.info("Shutdown requested (Ctrl+C).")
    logger.info("Server stopped")


if __name__ == "__main__":
    main()
