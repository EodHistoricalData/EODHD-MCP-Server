# entrypoints/server_stdio.py
import os
import argparse
import logging, sys
from pathlib import Path

# add project root to sys.path so `import app...` works
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from fastmcp import FastMCP
from app.tools import register_all

load_dotenv()  # Load .env first; CLI can override via env below.

def main() -> None:
    parser = argparse.ArgumentParser(description="EODHD MCP stdio server")
    parser.add_argument("--apikey", "--api-key", dest="api_key", help="EODHD API key")
    args = parser.parse_args()

    # If provided, override env so make_request() picks it up
    if args.api_key:
        os.environ["EODHD_API_KEY"] = args.api_key

    mcp = FastMCP("eodhd-datasets")
    register_all(mcp)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
    logger = logging.getLogger("eodhd-mcp")
    logger.info("Starting EODHD MCP stdio Server...")
    mcp.run(transport="stdio")
    logger.info("Server stopped")

if __name__ == "__main__":
    main()
