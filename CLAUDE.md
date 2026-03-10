# EODHD MCP Server v1

MCP server exposing 74 EODHD financial data API tools via HTTP, SSE, and stdio transports.

## Stack

Python 3.10+, FastMCP >=2.0, httpx (async HTTP), Ruff, MyPy, pytest, Bandit, Semgrep, pip-audit

## Commands

**Always use Docker** — do not rely on local Python/pip. This matches CI exactly.

```bash
# Helper: run any command in the project container
# Usage: docker run --rm -v "$(pwd):/app" -w /app python:3.10-slim sh -c '...'

# Install deps + run tests
docker run --rm -v "$(pwd):/app" -w /app python:3.10-slim sh -c \
  'pip install -r requirements.txt -r requirements-test.txt 2>&1 | tail -1 && \
   EODHD_API_KEY=test_key_for_ci pytest tests/ -v --tb=short'

# Install deps + run tests with coverage
docker run --rm -v "$(pwd):/app" -w /app python:3.10-slim sh -c \
  'pip install -r requirements.txt -r requirements-test.txt 2>&1 | tail -1 && \
   EODHD_API_KEY=test_key_for_ci pytest tests/ -v --cov=app --cov-report=term-missing'

# Lint + format + type check (all three)
docker run --rm -v "$(pwd):/app" -w /app python:3.10-slim sh -c \
  'pip install -r requirements.txt ruff mypy 2>&1 | tail -1 && \
   ruff check app/ server.py && \
   ruff format --check app/ server.py && \
   mypy app/ server.py --ignore-missing-imports --explicit-package-bases'

# Security scans
docker run --rm -v "$(pwd):/app" -w /app python:3.10-slim sh -c \
  'pip install -r requirements.txt bandit pip-audit semgrep 2>&1 | tail -1 && \
   bandit -r app/ -ll -ii -x app/resources/ && \
   semgrep scan --config p/python --config p/owasp-top-ten --config p/secrets --config p/jwt --error app/ && \
   pip-audit'

# Run server (local dev only)
python server.py                     # HTTP (default, port 8000)
python server.py --stdio             # stdio (Claude Desktop)
python server.py --sse               # SSE
python server.py --http --port 9000  # custom port
```

## Architecture

```
app/
  config.py           — env vars, API base URL
  api_client.py       — shared async httpx client, retry, rate-limit, auth injection
  validators.py       — input validation (ticker, exchange, date)
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
- Input validation: call `validate_ticker()`, `validate_exchange()`, `validate_date()` from `app/validators.py`
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

## Forbidden

- `print()` in app code (use `logging`; enforced by T20 rule)
- Direct API calls without going through `make_request()` in `api_client.py`
- Cross-tool imports (tools must not import from other tool modules)
- Hardcoded API keys
