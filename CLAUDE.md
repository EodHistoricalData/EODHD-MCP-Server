# EODHD MCP Server v1
MCP server exposing 74 EODHD financial data API tools via HTTP, SSE, and stdio transports.
## Stack
Python 3.10+, FastMCP >=2.0, httpx (async HTTP), Ruff, MyPy, pytest, Bandit, Semgrep, pip-audit
## Commands
```bash
# Always prefer .venv tools over system-wide
# Tests
.venv/bin/pytest tests/ -v --tb=short
.venv/bin/pytest tests/ -v --cov=app --cov-report=term-missing   # with coverage
# Lint & format
.venv/bin/ruff check app/ server.py
.venv/bin/ruff format --check app/ server.py
# Type checking
.venv/bin/mypy app/ server.py --ignore-missing-imports --explicit-package-bases
# Security
.venv/bin/bandit -r app/ -ll -ii -x app/resources/
semgrep scan --config p/python --config p/owasp-top-ten --config p/secrets --config p/jwt --error app/
.venv/bin/pip-audit
# Run server
.venv/bin/python server.py                     # HTTP (default, port 8000)
.venv/bin/python server.py --stdio             # stdio (Claude Desktop)
.venv/bin/python server.py --sse               # SSE
.venv/bin/python server.py --http --port 9000  # custom port
```
## Architecture
```
app/
  config.py           — env vars, API base URL
  api_client.py       — shared async httpx client, retry, rate-limit, auth injection
  formatter.py        — input sanitisation (ticker, exchange) and date coercion
  tools/              — 74 tool modules, each exports register(mcp)
    __init__.py       — ALL_TOOLS list, register_all(mcp), safe dynamic import
  prompts/            — example workflows (analyze_stock, compare_stocks, market_overview)
  resources/          — markdown reference docs exposed as MCP resources
server.py             — entry point, transport selection, argparse
```
### Tool categories
- `MAIN_TOOLS` — core EODHD endpoints (EOD, live, fundamentals, news, screener, etc.)
- `MARKETPLACE_TOOLS` — marketplace partner endpoints (options, indices, trading hours)
- `THIRD_PARTY_TOOLS` — illio, praams, investverte partner tools
## Conventions
- Every tool file exports `register(mcp: FastMCP)` — no exceptions
- All tools are read-only (`readOnlyHint=True`)
- Input sanitisation: call `sanitize_ticker()`, `sanitize_exchange()` from `app/formatter.py` (only reject URL-breaking chars; let API validate)
- Errors: raise `ToolError` for user-facing errors (MCP-native)
- API responses: return `json.dumps(data, indent=2)`
- Docstrings: every tool function has detailed docstring with Args, Returns, Examples
- Ruff ignores are documented with rationale in `pyproject.toml`
- `X | None` over `Optional[X]`
## HTTP Client (`api_client.py`)
- Single shared `httpx.AsyncClient` — reused across all tools
- Rate limiting: 100ms global delay (configurable)
- Retry: exponential backoff 1s/2s/4s (cap 10s), disabled by default (`EODHD_RETRY_ENABLED=true`)
- Auth: auto-injects `api_token` from URL > header > env var
- Token redaction in logs
## Testing
- pytest with `asyncio_mode="auto"`
- `respx` for HTTP mocking, `AsyncMock` for `make_request`
- Parametrized tests for URL construction and error paths across all 74 tools
- Coverage target: 50% (`fail_under` in pyproject.toml)
- Markers: `@pytest.mark.slow`, `@pytest.mark.integration`
- CI env: `EODHD_API_KEY=test_key_for_ci`
## CI Pipeline (GitHub Actions)
Three parallel jobs: lint (ruff + mypy), test (matrix 3.10/3.11/3.12/3.13), security (bandit + semgrep + pip-audit).
Concurrency: cancel-in-progress per ref.
## Git Hooks
- **pre-commit**: ruff check, ruff format --check, mypy — must all pass before commit
- **pre-push**: pytest — must pass before push
- Do NOT skip hooks with `--no-verify`
- If a hook fails, fix the issue and create a NEW commit (never amend the previous one to work around it)
## Forbidden
- `print()` in app code (use `logging`; enforced by T20 rule)
- Direct API calls without going through `make_request()` in `api_client.py`
- Cross-tool imports (tools must not import from other tool modules)
- Hardcoded API keys
