# tests/manual/test_client_stdio.py
import argparse
import asyncio
import json
import os
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

# Make project root importable (so "all_tests" etc. can be found)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------- Common defaults ----------
COMMON: dict[str, Any] = {
    # "api_token": "PLACE_YOUR_API_TOKEN_HERE",
    "api_token": os.getenv("EODHD_API_KEY"),
    "fmt": "json",
    "ticker": "AAPL.US",
    "start_date": "2023-01-01",
    "end_date": "2023-02-01",
    "limit": 5,
    "offset": 0,
}

# ---------- Test registry ----------
Test = dict[str, Any]
TESTS: list[Test] = []


def register_test(test: Test) -> None:
    if "name" not in test or "tool" not in test:
        raise ValueError("Test must include 'name' and 'tool'.")
    TESTS.append(test)


def _build_params(test: Test) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for key in test.get("use_common", []):
        if key in COMMON and COMMON[key] is not None:
            params[key] = COMMON[key]
    params.update(test.get("params", {}))
    return params


# ---------- Load manual modules ----------
_env_list = os.getenv("MCP_TEST_MODULES")
TEST_MODULES = [m.strip() for m in _env_list.split(",")] if _env_list else ["all_tests"]


def _load_test_modules() -> None:
    for mod_name in TEST_MODULES:
        mod = import_module(mod_name)
        if hasattr(mod, "register") and callable(mod.register):
            mod.register(register_test, COMMON)
        else:
            raise RuntimeError(f"Test module '{mod_name}' must define 'register(register_fn, COMMON)'.")


# ---------- Pretty print ----------
def _pp(obj: Any) -> str:
    try:
        if isinstance(obj, (dict, list)):
            return json.dumps(obj, indent=2, ensure_ascii=False)
        if isinstance(obj, str):
            try:
                parsed = json.loads(obj)
                return json.dumps(parsed, indent=2, ensure_ascii=False)
            except Exception:
                return obj
        return str(obj)
    except Exception:
        return str(obj)


# ---------- MCP stdio client ----------
import shlex

from mcp.client.session import ClientSession  # type: ignore
from mcp.client.stdio import StdioServerParameters, stdio_client  # type: ignore


async def _run_suite(session: ClientSession) -> None:
    tools_resp = await session.list_tools()
    tool_names = [t.name for t in getattr(tools_resp, "tools", [])]
    print("Available tools:", tool_names)

    print("\n=== Running auto (STDIO) ===")
    for idx, test in enumerate(TESTS, start=1):
        name = test["name"]
        tool = test["tool"]
        params = _build_params(test)

        print(f"\n[{idx}] {name}  ➜  {tool}")
        print("Params:", _pp(params))

        try:
            result = await session.call_tool(tool, params)

            parts: list[str] = []
            for c in getattr(result, "content", []) or []:
                ctype = getattr(c, "type", None)
                if ctype == "text" and hasattr(c, "text"):
                    parts.append(str(c.text))
                elif ctype == "json" and hasattr(c, "json"):
                    parts.append(_pp(c.json))
                else:
                    parts.append(_pp(c))
            print("Result:\n", "\n".join(parts) if parts else _pp(result))
        except Exception as e:
            print("ERROR:", e)


async def run_tests_stdio(cmdline: str) -> None:
    """
    cmdline: full command as ONE string, e.g.
      "python -m entrypoints.server_stdio --apikey 68e1d0927848e6.45930006"
    """
    _load_test_modules()

    # Parse the command string into executable + args for StdioServerParameters
    tokens = shlex.split(cmdline)
    server = StdioServerParameters(
        command=tokens[0],
        args=tokens[1:],
        cwd=str(ROOT),
    )
    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        await _run_suite(session)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MCP tool auto against STDIO server.")
    parser.add_argument(
        "--cmd",
        dest="stdio_cmd",
        default=os.getenv("MCP_STDIO_CMD", "python -m entrypoints.server_stdio"),
        help="Full command to launch the stdio server (single string). "
        'Example: "python -m entrypoints.server_stdio --apikey YOUR_KEY".',
    )
    parser.add_argument(
        "--apikey",
        "--api-key",
        dest="api_key",
        default=None,
        help="EODHD API key (overrides EODHD_API_KEY env var).",
    )
    args = parser.parse_args()
    if args.api_key:
        COMMON["api_token"] = args.api_key
    asyncio.run(run_tests_stdio(args.stdio_cmd))


if __name__ == "__main__":
    main()
