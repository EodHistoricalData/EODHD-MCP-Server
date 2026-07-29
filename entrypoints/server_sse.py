# entrypoints/server_sse.py

import os
import logging, sys
from pathlib import Path

# add project root to sys.path so `import app...` works
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from fastmcp import FastMCP
from app.api_client import TokenRedactingFilter
from app.tools import register_all

load_dotenv()

def main() -> None:
    # Same server + tools as before
    mcp = FastMCP("eodhd-datasets")
    register_all(mcp)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
    for handler in logging.getLogger().handlers:
        handler.addFilter(TokenRedactingFilter())
    # httpx logs every request URL at INFO, which puts the caller's search parameters
    # (tickers, member ids, date ranges) into operational logs. api_client already logs a
    # redacted URL at DEBUG, so nothing is lost by keeping httpx quiet.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logger = logging.getLogger("eodhd-mcp")

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", 8000))

    logger.info("Starting EODHD MCP **SSE** Server on %s:%d ...", host, port)

    mcp.run(transport="sse", host=host, port=port)

    logger.info("Server stopped")

if __name__ == "__main__":
    main()
