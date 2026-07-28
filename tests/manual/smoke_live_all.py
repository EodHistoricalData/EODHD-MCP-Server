#!/usr/bin/env python3
"""Live smoke over every registered tool, through a real MCP client.

Needs a working EODHD_API_KEY (read from the repo .env). For each tool it records the
outcome, the response size and whether the API key leaked into the payload, then writes
a machine-readable report next to this file.

Usage:
    python tests/manual/smoke_live_all.py                 # skips the three report tools
    python tests/manual/smoke_live_all.py --with-writes   # also generates/emails reports
    python tests/manual/smoke_live_all.py --report out.json

The three Praams report tools are skipped by default because they generate a PDF and email
it to the address passed in, which is a side effect a smoke run should not trigger silently.
"""

import argparse
import ast
import asyncio
import json
import os
import pathlib
import sys
import time
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from app.tools import register_all
from fastmcp import Client, FastMCP

# The parametrized URL tests already carry valid arguments for most tools; reuse them so
# this script does not drift from the suite.
_TESTS = (REPO_ROOT / "tests/auto/test_tools.py").read_text()
_BLOCK = _TESTS[_TESTS.index("URL_CASES = [") : _TESTS.index("\n]", _TESTS.index("URL_CASES = [")) + 2]
ARGS: dict[str, dict[str, Any]] = {
    case[0]: case[1] for case in reversed(ast.literal_eval(_BLOCK.split("=", 1)[1].strip()))
}

# Tools with no URL case, plus overrides where the generic case would pull a full history
# or hit an endpoint that needs a specific instrument type.
ARGS.update(
    {
        "capture_realtime_ws": {"feed": "us_quotes", "symbols": "AAPL", "duration_seconds": 5, "max_messages": 2},
        "get_fundamentals_data": {"ticker": "AAPL.US", "sections": ["General"]},
        "get_historical_stock_prices": {"ticker": "AAPL.US", "start_date": "2026-07-01", "end_date": "2026-07-15"},
        "get_intraday_historical_data": {
            "ticker": "AAPL.US",
            "interval": "1h",
            "from_timestamp": "2026-07-01",
            "to_timestamp": "2026-07-03",
        },
        "get_mp_praams_bond_analyze_by_isin": {"isin": "US7593518852"},
        "get_support_resistance_levels": {"ticker": "AAPL.US"},
        "get_us_options_contracts": {"underlying_symbol": "AAPL", "page_limit": 5},
        "get_us_options_eod": {"underlying_symbol": "AAPL", "page_limit": 5},
        "retrieve_description_by_id": {"type": 2, "id": 1},
    }
)

WRITE_TOOLS = {
    "get_mp_praams_report_bond_by_isin",
    "get_mp_praams_report_equity_by_isin",
    "get_mp_praams_report_equity_by_ticker",
}

# Claude truncates a tool result at roughly this many characters.
RESPONSE_BUDGET = 150_000

PERMISSION_MARKERS = ("status_code=402", "status_code=403", "subscription", "not available for your plan")


def _classify(message: str) -> str:
    lowered = message.lower()
    if any(marker in lowered for marker in PERMISSION_MARKERS):
        return "plan_or_permission"
    if "status_code=404" in lowered or "not found" in lowered:
        return "upstream_not_found"

    return "failed"


def _payload(result: Any, secret: str) -> tuple[int, str, bool]:
    blocks = result.content if hasattr(result, "content") else result
    if not blocks:
        return 0, "", False
    resource = getattr(blocks[0], "resource", blocks[0])
    text = getattr(resource, "text", None)
    if text is not None:
        return len(text), text[:160], secret in text
    blob = str(getattr(resource, "blob", "") or "")

    return len(blob), f"<binary {len(blob)}>", secret in blob


async def run(include_writes: bool, report_path: pathlib.Path) -> int:
    secret = os.environ.get("EODHD_API_KEY") or ""
    if not secret:
        print("EODHD_API_KEY is not set (put it in .env)", file=sys.stderr)

        return 2

    mcp: FastMCP = FastMCP("smoke-live-all")
    register_all(mcp)
    rows: list[dict[str, Any]] = []

    async with Client(mcp) as client:
        tools = sorted(await client.list_tools(), key=lambda tool: tool.name)
        print(f"registered tools: {len(tools)}")
        for tool in tools:
            if tool.name in WRITE_TOOLS and not include_writes:
                rows.append({"tool": tool.name, "status": "skipped_write_tool", "size": 0, "key_leaked": False})
                print(f"  {'skipped_write_tool':20} {tool.name}")
                continue
            args = ARGS.get(tool.name)
            if args is None:
                rows.append({"tool": tool.name, "status": "no_args", "size": 0, "key_leaked": False})
                print(f"  {'no_args':20} {tool.name}")
                continue

            started = time.monotonic()
            try:
                result = await client.call_tool(tool.name, dict(args))
                size, head, leaked = _payload(result, secret)
                status, detail = "ok", head
            except Exception as exc:
                detail = str(exc)
                size, leaked, status = 0, secret in detail, _classify(detail)

            rows.append(
                {
                    "tool": tool.name,
                    "status": status,
                    "size": size,
                    "over_budget": size > RESPONSE_BUDGET,
                    "key_leaked": leaked,
                    "seconds": round(time.monotonic() - started, 2),
                    "args": args,
                    "detail": detail.replace(secret, "***")[:300],
                }
            )
            print(f"  {status:20} {tool.name:44} {size:>9} chars")

    report_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    leaked = [row["tool"] for row in rows if row.get("key_leaked")]
    over_budget = [(row["tool"], row["size"]) for row in rows if row.get("over_budget")]

    print(f"\nsummary: {json.dumps(counts)}")
    print(f"api key leaked into payload: {leaked or 'none'}")
    print(f"responses over {RESPONSE_BUDGET} chars: {over_budget or 'none'}")
    print(f"report: {report_path}")

    return 1 if leaked or counts.get("failed") else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-writes", action="store_true", help="also call the report tools (sends email)")
    parser.add_argument("--report", default=str(pathlib.Path(__file__).with_name("smoke_live_all_report.json")))

    args = parser.parse_args()

    return asyncio.run(run(args.with_writes, pathlib.Path(args.report)))


if __name__ == "__main__":
    raise SystemExit(main())
