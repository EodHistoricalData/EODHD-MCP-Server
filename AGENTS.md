# EODHD MCP Server v1

MCP server exposing 74 EODHD financial data API tools via HTTP, SSE, and stdio transports.

## Stack

Python 3.11+, FastMCP >=2.0, httpx (async HTTP), Ruff, MyPy, pytest, Bandit, Semgrep, pip-audit

## Commands

```bash
pytest tests/ -v --tb=short                              # run tests
pytest tests/ -v --cov=app --cov-report=term-missing     # with coverage
ruff check app/ server.py                                # lint
ruff format --check app/ server.py                       # format check
mypy app/ server.py --ignore-missing-imports             # type check
bandit -r app/ -ll -ii -x app/resources/                 # security scan (AST)
semgrep scan --config p/python --config p/owasp-top-ten --config p/secrets --config p/jwt --error app/  # SAST + taint
python server.py                                         # run (HTTP, port 8000)
python server.py --stdio                                 # run (stdio)
```

## Architecture

- `server.py` — entry point, transport selection
- `app/config.py` — env vars, API base URL
- `app/api_client.py` — shared async httpx client with retry, rate-limit, auth injection
- `app/validators.py` — input validation (ticker, exchange, date regex)
- `app/tools/` — 74 tool modules, each exports `register(mcp: FastMCP)`
- `app/tools/__init__.py` — `ALL_TOOLS` list, `register_all(mcp)`, safe dynamic import
- `app/prompts/` — example workflows
- `app/resources/` — markdown reference docs as MCP resources

## Key Rules

- Every tool file must export `register(mcp)` — called by `register_all()`
- All tools are read-only (`readOnlyHint=True`)
- Validate inputs via `validate_ticker()`, `validate_exchange()`, `validate_date()` from `app/validators.py`
- Raise `ToolError` for user-facing errors
- Return `json.dumps(data, indent=2)` from tools
- All HTTP calls go through `make_request()` in `api_client.py` — never call httpx directly
- No cross-tool imports (tools must not import from other tool modules)
- No `print()` in app code — use `logging`
- Use `X | None` not `Optional[X]`

## Testing

- pytest, asyncio_mode="auto", `respx` for HTTP mocking
- Parametrized tests for URL construction and error paths
- Coverage target: 50% (pyproject.toml `fail_under`)
- CI uses `EODHD_API_KEY=test_key_for_ci`
