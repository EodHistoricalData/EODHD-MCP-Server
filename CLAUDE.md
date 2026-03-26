# EODHD MCP Server v1
MCP server exposing 75 EODHD financial data API tools via HTTP, SSE, and stdio transports.

## Stack
Python 3.10+, FastMCP >=2.0, httpx (async HTTP), Ruff, MyPy, pytest, Bandit, Semgrep, pip-audit

## Commands
```bash
# Tests
pytest tests/auto/ -v --tb=short
pytest tests/auto/ -v --cov=app --cov-report=term-missing

# Lint & format
ruff check app/ server.py
ruff format --check app/ server.py

# Type checking
mypy app/ server.py --ignore-missing-imports --explicit-package-bases

# Security
bandit -r app/ -ll -ii -x app/resources/
semgrep scan --config p/python --config p/owasp-top-ten --config p/secrets --config p/jwt --error app/
pip-audit --ignore-vuln CVE-2026-4539

# Run server
python server.py
python server.py --stdio
python server.py --sse
python server.py --http --port 9000
```

## Architecture
```text
app/
  config.py           - env vars, API base URL
  api_client.py       - shared async httpx client, retry, rate-limit, auth injection
  input_formatter.py  - input sanitisation, date coercion, URL helpers
  response_formatter.py - MCP EmbeddedResource formatting and API error raising
  tools/              - 75 tool modules, each exports register(mcp)
    __init__.py       - ALL_TOOLS list, register_all(mcp), safe dynamic import
  prompts/            - example workflows
  resources/          - markdown reference docs exposed as MCP resources
server.py             - entry point, transport selection, argparse
```

## Tool Categories
- `MAIN_TOOLS` - core EODHD endpoints
- `MARKETPLACE_TOOLS` - marketplace partner endpoints
- `THIRD_PARTY_TOOLS` - illio, praams, investverte partner tools

## Conventions
- Every tool file exports `register(mcp: FastMCP)`.
- All tools are read-only (`readOnlyHint=True`).
- Sanitize inputs with helpers from `app/input_formatter.py`.
- Raise `ToolError` for user-facing failures.
- Route all HTTP traffic through `make_request()` in `app/api_client.py`.
- Return MCP resources via `response_formatter` helpers, not raw `json.dumps`.
- Preserve explicit upstream API errors; do not silently pass through `{"error": ...}` payloads as successful results.
- No cross-tool imports.
- No `print()` in app code; use `logging`.
- Use `X | None` instead of `Optional[X]`.

## HTTP Client
- Shared `httpx.AsyncClient`
- Per-connection rate limiting disabled by default; enable with `EODHD_RATE_LIMIT_DELAY=0.1` (seconds)
- Retries disabled by default unless `EODHD_RETRY_ENABLED=true`
- Auth resolution order: URL `api_token` > HTTP request auth/header/query params > env var
- API token values are redacted in logs

### Error handling — by design `make_request()` returns dicts, not exceptions
`make_request()` returns `{"error": ...}` dicts on failure **by design**. This is
intentional and must not be "fixed" to raise exceptions. Rationale:

- EODHD API errors (404 "Ticker Not Found", 403 plan limits, etc.) are **upstream
  data responses**, not MCP server errors. The calling AI agent needs the full
  context (status code, error message, upstream details) to make decisions — e.g.
  correct a ticker, try a different endpoint, or inform the user.
- Raising exceptions would lose this context and incorrectly treat normal API
  responses as server failures.
- The safety net is `format_json_response()` → `raise_on_api_error()` in
  `response_formatter.py`, which converts error dicts into `ToolError` when the
  response is being returned to the agent. Tools that need to inspect the error
  before deciding (e.g. to try a fallback) can do so before calling the formatter.

## Testing
- `pytest` with `asyncio_mode="auto"`
- `respx` for HTTP mocking, `AsyncMock` for `make_request`
- Parametrized coverage for URL construction and error paths
- Coverage target: 60%
- CI env: `EODHD_API_KEY=test_key_for_ci`

## CI Pipeline
Three jobs: lint, test, security.
- Lint: Python 3.10, Ruff + MyPy
- Test: Python 3.10/3.11/3.12/3.13, `pytest tests/auto/`
- Security: Bandit, Semgrep, pip-audit

## Forbidden
- Direct HTTP calls outside `api_client.py`
- Cross-tool imports
- Hardcoded API keys
- Changing `make_request()` to raise exceptions instead of returning error dicts (see "Error handling" above)

## Bridge AI
Multi-AI orchestrator with 16 providers and 128 skills.

**Model routing (BDRR):** auto-selects best AI by task - cheap models (DeepSeek, Nova) for simple tasks, powerful (GPT-5.4, Claude, Gemini Pro) for complex. Saves budget.

**Skill routing:** 128 domain skills (engineering, sales, finance, legal, marketing, data, design, ops, HR, product) with 100% accuracy.

**Usage:**
- `bridge_smart(topic)` - auto-select model + mode
- `bridge_smart(topic, profile="power")` - force powerful models
- `bridge_council(topic)` - 6 AI council for architecture/strategy
- `bridge_debate(topic)` - pro/con debate for decisions
- `bridge_ask(perplexity, question)` - fact-check with citations
- `bridge_ask(deepseek-r1, question)` - math/logic reasoning
- `bridge_ideas(topic)` - creative brainstorming (7+ AI providers)
- `bridge_dev_loop(topic)` - iterative dev with Writer+Reviewer+Tester

**Brain (filtered):** call `brain_query(project="<project-name>", zone="business")` at session start for cross-project lessons (code patterns, architecture, security only - no personal data).
