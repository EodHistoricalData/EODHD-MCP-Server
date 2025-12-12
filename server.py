import argparse
import logging
import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP
from app.tools import register_all


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="EODHD MCP Server")

    # Transport selection (mutually exclusive): default is HTTP unless --stdio is provided
    transport = p.add_mutually_exclusive_group()
    transport.add_argument(
        "--http",
        action="store_true",
        help="Run HTTP transport (default).",
    )
    transport.add_argument(
        "--stdio",
        action="store_true",
        help="Run STDIO transport (only if explicitly requested).",
    )

    # Defaults come from environment variables (loaded from .env), but CLI overrides env
    p.add_argument(
        "--host",
        default=os.getenv("MCP_HOST", "127.0.0.1"),
        help="HTTP host (default: 127.0.0.1 or $MCP_HOST).",
    )
    p.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "8000")),
        help="HTTP port (default: 8000 or $MCP_PORT).",
    )
    p.add_argument(
        "--path",
        default=os.getenv("MCP_PATH", "/mcp"),
        help="HTTP path (default: /mcp or $MCP_PATH).",
    )
    p.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Logging level (default: INFO or $LOG_LEVEL).",
    )

    p.add_argument(
        "--apikey", "--api-key",
        dest="api_key",
        help="EODHD API key")

    return p



def main(argv: list[str] | None = None) -> int:
    # Load .env before parsing so env defaults are available to argparse
    load_dotenv()
    parser = build_parser()
    args, unknown = parser.parse_known_args(argv)
    # If provided, override env so make_request() picks it up
    if args.api_key:
        os.environ["EODHD_API_KEY"] = args.api_key

    if unknown:
        # Don’t print secrets; just show shapes
        print(f"Ignoring extra args from client: {len(unknown)} item(s)", file=sys.stderr)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
    logger = logging.getLogger("eodhd-mcp")

    mcp = FastMCP("eodhd-datasets")
    register_all(mcp)

    # Determine transport: default to HTTP unless --stdio was given
    run_stdio = args.stdio
    run_http = args.http or not args.stdio

    try:
        if run_stdio:
            logger.info("Starting EODHD MCP (STDIO)...")
            mcp.run(transport="stdio")
            logger.info("STDIO server stopped.")
            return 0

        if run_http:
            logger.info(
                "Starting EODHD MCP HTTP Server on http://%s:%s%s ...",
                args.host,
                args.port,
                args.path,
            )
            mcp.run(
                transport="streamable-http",
                host=args.host,
                port=args.port,
                path=args.path,
            )
            logger.info("HTTP server stopped.")
            return 0

        logger.error("No transport selected.")
        return 2

    except KeyboardInterrupt:
        logger.info("Shutdown requested (Ctrl+C).")
        return 0
    except Exception:
        logger.exception("Fatal error while running MCP server.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
