# test_client_sse.py

import asyncio
import json
import os
from importlib import import_module
from typing import Any, Dict, List

from fastmcp import Client

# ---------- Common defaults ----------
COMMON: Dict[str, Any] = {
    "api_token": os.getenv("EODHD_API_KEY", "demo"),
    #"api_token": "PLACE_YOUR_API_TOKEN_HERE",
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
    use_common = test.get("use_common", [])
    for key in use_common:
        if key in COMMON and COMMON[key] is not None:
            params[key] = COMMON[key]
    params.update(test.get("params", {}))
    return params

# ---------- Where to load tests from ----------
TEST_MODULES = [
    "all_tests_beta",
    "all_tests",# add more like "eod", "intraday", etc.
]

def _load_test_modules() -> None:
    for mod_name in TEST_MODULES:
        mod = import_module(mod_name)
        if hasattr(mod, "register") and callable(mod.register):
            mod.register(register_test, COMMON)
        else:
            raise RuntimeError(
                f"Test module '{mod_name}' must define a callable 'register(register_fn, COMMON)'."
            )

# ---------- Pretty-print helper ----------
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

# ---------- Runner ----------
async def run_tests(
    endpoint: str | None = None,
) -> None:
    _load_test_modules()

    # Default to your SSE endpoint
    if endpoint is None:
        endpoint = os.getenv("MCP_ENDPOINT", "http://127.0.0.1:8000/sse")

    print(f"Connecting to MCP server at {endpoint} (SSE)...")

    async with Client(endpoint) as client:
        tools = await client.list_tools()
        print("Available tools:", [getattr(t, "name", t) for t in tools])

        print("\n=== Running tests ===")
        for idx, test in enumerate(TESTS, start=1):
            name = test["name"]
            tool = test["tool"]
            params = _build_params(test)

            print(f"\n[{idx}] {name}  ➜  {tool}")
            print("Params:", _pp(params))

            try:
                result = await client.call_tool(tool, params)
                print("Result:\n", _pp(result))
            except Exception as e:
                print("ERROR:", e)

# ---------- CLI entry ----------
if __name__ == "__main__":
    import sys

    cli_endpoint = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(run_tests(endpoint=cli_endpoint))
