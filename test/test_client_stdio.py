# test_client_stdio.py
import asyncio
import json
import os
import argparse
import sys
from pathlib import Path
from importlib import import_module
from typing import Any, Dict, List

# Make project root importable (so "all_tests" etc. can be found)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------- Common defaults ----------
COMMON: Dict[str, Any] = {
    #"api_token": "PLACE_YOUR_API_TOKEN_HERE",
    "api_token": os.getenv("EODHD_API_KEY", "demo"),
    "fmt": "json",
    "ticker": "AAPL.US",
    "start_date": "2023-01-01",
    "end_date": "2023-02-01",
    "limit": 5,
    "offset": 0,
}

# ---------- Test registry ----------
Test = Dict[str, Any]
TESTS: List[Test] = []

def register_test(test: Test) -> None:
    if "name" not in test or "tool" not in test:
        raise ValueError("Test must include 'name' and 'tool'.")
    TESTS.append(test)

def _build_params(test: Test) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    for key in test.get("use_common", []):
        if key in COMMON and COMMON[key] is not None:
            params[key] = COMMON[key]
    params.update(test.get("params", {}))
    return params

# ---------- Load test modules ----------
_env_list = os.getenv("MCP_TEST_MODULES")
TEST_MODULES = [m.strip() for m in _env_list.split(",")] if _env_list else ["all_tests"]

def _load_test_modules() -> None:
    for mod_name in TEST_MODULES:
        mod = import_module(mod_name)
        if hasattr(mod, "register") and callable(mod.register):
            mod.register(register_test, COMMON)
        else:
            raise RuntimeError(
                f"Test module '{mod_name}' must define 'register(register_fn, COMMON)'."
            )

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

# ---------- MCP stdio client (compat with multiple mcp versions) ----------
from mcp.client.session import ClientSession  # type: ignore
from mcp.client.stdio import stdio_client  # type: ignore

# Try to import StdioServer (newer mcp); if not present, we'll still try with raw string.
try:
    from mcp.client.stdio import StdioServer  # type: ignore
    HAVE_STDIO_SERVER = True
except Exception:
    HAVE_STDIO_SERVER = False

async def _run_suite(session: ClientSession) -> None:
    await session.initialize()

    tools_resp = await session.list_tools()
    tool_names = [t.name for t in getattr(tools_resp, "tools", [])]
    print("Available tools:", tool_names)

    print("\n=== Running tests (STDIO) ===")
    for idx, test in enumerate(TESTS, start=1):
        name = test["name"]
        tool = test["tool"]
        params = _build_params(test)

        print(f"\n[{idx}] {name}  ➜  {tool}")
        print("Params:", _pp(params))

        try:
            results = await session.call_tool(tool, params)

            parts: List[str] = []
            for r in results or []:
                for c in getattr(r, "content", []) or []:
                    ctype = getattr(c, "type", None)
                    if ctype == "text" and hasattr(c, "text"):
                        parts.append(str(c.text))
                    elif ctype == "json" and hasattr(c, "json"):
                        parts.append(_pp(c.json))
                    else:
                        parts.append(_pp(c))
            print("Result:\n", "\n".join(parts) if parts else _pp(results))
        except Exception as e:
            print("ERROR:", e)

    try:
        await session.close()
    except Exception:
        pass

async def run_tests_stdio(cmdline: str) -> None:
    """
    cmdline: full command as ONE string, e.g.
      "python -m entrypoints.server_stdio --apikey 68e1d0927848e6.45930006"
    """
    _load_test_modules()

    # Prefer the new-style API that takes a StdioServer, and fall back to
    # the old API (which takes a raw string) only if needed.
    if HAVE_STDIO_SERVER:
        try:
            server = StdioServer(command=cmdline)  # newer mcp expects this
            async with stdio_client(server) as (read, write):
                session = ClientSession(read, write)
                await _run_suite(session)
                return
        except TypeError:
            # Some older builds accept only a raw string; fall back below.
            pass

    # Fallback: older mcp that expects a raw string command
    async with stdio_client(cmdline) as (read, write):
        session = ClientSession(read, write)
        await _run_suite(session)

def main() -> None:
    parser = argparse.ArgumentParser(description="Run MCP tool tests against STDIO server.")
    parser.add_argument(
        "--cmd",
        dest="stdio_cmd",
        default=os.getenv("MCP_STDIO_CMD", "python -m entrypoints.server_stdio"),
        help='Full command to launch the stdio server (single string). '
             'Example: "python -m entrypoints.server_stdio --apikey YOUR_KEY".',
    )
    args = parser.parse_args()
    asyncio.run(run_tests_stdio(args.stdio_cmd))

if __name__ == "__main__":
    main()
