import asyncio
import json
import os
from importlib import import_module
from typing import Any, Callable, Dict, List, Optional

from fastmcp import Client

# ---------- Common defaults (can be overridden per test) ----------
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
    """
    Register a test.

    test = {
      "name": "Human-friendly name",
      "tool": "get_historical_stock_prices",
      "use_common": ["api_token", "fmt", "ticker", "start_date", "end_date"],  # optional list
      "params": { ... overrides / specific params ... }
    }
    """
    if "name" not in test or "tool" not in test:
        raise ValueError("Test must include 'name' and 'tool'.")
    TESTS.append(test)

def _build_params(test: Test) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    use_common = test.get("use_common", [])
    for key in use_common:
        if key in COMMON and COMMON[key] is not None:
            params[key] = COMMON[key]
    # Apply specific params (override COMMON if collisions)
    params.update(test.get("params", {}))
    return params

# ---------- Where to load tests from (single registration point) ----------
TEST_MODULES = [
    "all_tests_beta",
    "all_tests",# add more like "eod", "intraday", etc.
]

def _load_test_modules() -> None:
    for mod_name in TEST_MODULES:
        mod = import_module(mod_name)
        # each module must expose: register(register_fn, COMMON_defaults)
        if hasattr(mod, "register") and callable(mod.register):
            mod.register(register_test, COMMON)
        else:
            raise RuntimeError(f"Test module '{mod_name}' must define a callable 'register(register_fn, COMMON)'.")

# ---------- Pretty print helpers ----------
def _pp(obj: Any) -> str:
    try:
        if isinstance(obj, (dict, list)):
            return json.dumps(obj, indent=2, ensure_ascii=False)
        # try to parse JSON-ish strings returned by server
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
async def run_tests(endpoint: str = "http://127.0.0.1:8000/mcp") -> None:
    _load_test_modules()

    async with Client(endpoint) as client:
        tools = await client.list_tools()
        print("Available tools:", [t["name"] if isinstance(t, dict) else t for t in tools])

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
    asyncio.run(run_tests())
