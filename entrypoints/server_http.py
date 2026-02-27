# entrypoints/server_http.py
import os
import logging, sys
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
    mcp = FastMCP("eodhd-datasets")
    register_all(mcp)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
    logger = logging.getLogger("eodhd-mcp")
    logger.info("Starting EODHD MCP HTTP Server...")
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", 8000))
    mcp.run(transport="streamable-http", host=host, port=port, path="/mcp")
    logger.info("Server stopped")

if __name__ == "__main__":
    main()
