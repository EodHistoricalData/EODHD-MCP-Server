<a href="https://eodhistoricaldata.com/">
  <div align="center">
    <picture>
      <source media="(prefers-color-scheme: light)" srcset="assets/icon.png">
      <source media="(prefers-color-scheme: dark)" srcset="assets/icon.svg">
      <img alt="EODHD logo" src="assets/icon.png" height="90">
    </picture>
  </div>
</a>
<br>

# EODHD MCP Server

Model Context Protocol (MCP) server for [EOD Historical Data](https://eodhd.com/) APIs.

The current server exposes **75 read-only MCP tools** across three transports:

- `streamable-http` via `server.py` on `/mcp` by default
- `sse`
- `stdio`

It also ships bundled MCP prompts and documentation resources.

## Coverage

### Core datasets

- End-of-day, intraday, and US tick data
- Live quotes and US Live v2 extended quotes
- Fundamentals, earnings, and financial statements
- Company news, sentiment, and news word weights
- Screeners, search, and technical indicators
- Corporate actions: IPOs, splits, dividends, symbol changes
- Macro indicators, economic events, exchanges, and listings
- CBOE index tools
- Treasury bill, yield, real yield, and long-term rates

### Marketplace and partner datasets

- US options: contracts, EOD, and underlyings
- illio: performance, risk, and market insights
- Praams: risk scoring, bonds, bank statements, reports, screeners
- Investverte ESG: companies, countries, and sectors
- TradingHours market lookup, market details, and status

## Current Behavior

- All tools are read-only and register through `app/tools/__init__.py`.
- All HTTP requests go through the shared async client in `app/api_client.py`.
- Upstream API errors are preserved as MCP `ToolError`s with status code and upstream details where available.
- API tokens are injected into EODHD requests as `api_token=...` query parameters.
- Optional retry support is controlled by `EODHD_RETRY_ENABLED` or per-call settings in code.

## Requirements

- Python `3.10+`
- A valid EODHD API key
- An MCP-compatible client such as Claude Desktop, Claude Code, ChatGPT MCP/Connectors, or MCP Inspector

## Installation

```bash
git clone https://github.com/EodHistoricalData/EODHD-MCP-Server.git
cd EODHD-MCP-Server
pip install -r requirements.txt
```

For development tooling:

```bash
pip install -e ".[dev]"
```

Create a `.env` file at the repository root:

```env
EODHD_API_KEY=YOUR_EODHD_API_KEY
MCP_HOST=127.0.0.1
MCP_PORT=8000
MCP_PATH=/mcp
LOG_LEVEL=INFO
# Optional:
EODHD_RETRY_ENABLED=false
```

## Running the Server

### Recommended entrypoint

`server.py` is the main maintained entrypoint.

Run HTTP (default):

```bash
python server.py
```

Run HTTP explicitly:

```bash
python server.py --http --host 127.0.0.1 --port 8000 --path /mcp
```

Run SSE:

```bash
python server.py --sse
```

Run stdio:

```bash
python server.py --stdio
```

Override the API key from the CLI:

```bash
python server.py --stdio --apikey YOUR_EODHD_API_KEY
```

### Compatibility entrypoints

The repo still includes legacy compatibility entrypoints in `entrypoints/`:

```bash
python -m entrypoints.server_http
python -m entrypoints.server_sse
python -m entrypoints.server_stdio --apikey YOUR_EODHD_API_KEY
```

These are still usable, but `server.py` is the primary runtime surface.

## Authentication Model

For outgoing EODHD requests, the server ultimately sends the token as `api_token` in the query string.

For incoming HTTP MCP requests, the server can resolve the EODHD token from:

- `Authorization: Bearer <token>`
- `X-API-Key: <token>`
- query params: `apikey`, `api_key`, or `token`
- fallback server environment: `EODHD_API_KEY`

Many tools also expose an explicit `api_token` argument for per-call override.

## Using with Claude Desktop

### Packaged extension

The packaged MCP manifest uses the stdio entrypoint in `manifest.json`.

### Source checkout example

```json
{
  "mcpServers": {
    "eodhd-mcp": {
      "command": "python3",
      "args": [
        "/absolute/path/to/EODHD-MCP-Server/server.py",
        "--stdio"
      ],
      "env": {
        "EODHD_API_KEY": "YOUR_EODHD_API_KEY"
      }
    }
  }
}
```

## Using with ChatGPT MCP / Connectors

For local HTTP testing, use:

- URL: `http://127.0.0.1:8000/mcp`

If your MCP client supports headers, you can provide the EODHD token via `Authorization: Bearer ...` or `X-API-Key: ...`. Otherwise, set `EODHD_API_KEY` on the server.

## Development Commands

```bash
pytest tests/auto/ -v --tb=short
pytest tests/auto/ -v --cov=app --cov-report=term-missing
ruff check app/ server.py
ruff format --check app/ server.py
mypy app/ server.py --ignore-missing-imports --explicit-package-bases
bandit -r app/ -ll -ii -x app/resources/
semgrep scan --config p/python --config p/owasp-top-ten --config p/secrets --config p/jwt --error app/
python server.py
python server.py --stdio
```

## Manual End-to-End Clients

The repository includes manual MCP clients in `tests/manual/`.

Start the main server in one terminal:

```bash
python server.py
```

Then run the HTTP manual client:

```bash
python tests/manual/test_client_http.py --endpoint http://127.0.0.1:8000/mcp
```

For SSE:

```bash
python server.py --sse
python tests/manual/test_client_sse.py --endpoint http://127.0.0.1:8000/sse
```

For stdio:

```bash
python tests/manual/test_client_stdio.py --cmd "python server.py --stdio --apikey YOUR_EODHD_API_KEY"
```

Manual test catalogs are loaded from `tests/manual/all_tests.py` by default.

## Docker

Run with Docker Compose:

```bash
docker compose up --build
```

The compose service starts `python server.py` and maps `${MCP_PORT_OUT}` to `${MCP_PORT}`.

## Project Layout

- `server.py` — main entrypoint and transport selection
- `app/api_client.py` — shared async HTTP client, auth injection, rate limiting, retry logic
- `app/response_formatter.py` — MCP resource formatting and API error raising
- `app/input_formatter.py` — input sanitization and date coercion
- `app/tools/` — MCP tool implementations
- `app/prompts/` — bundled MCP prompts
- `app/resources/` — bundled MCP resources and reference docs
- `tests/auto/` — automated tests
- `tests/manual/` — manual end-to-end MCP clients

## Notes

- Some marketplace endpoints require specific EODHD subscription access.
- A valid API key can still receive upstream permission errors for tools or watchlists not included in the account plan.
- The server now preserves those upstream reasons in agent-visible tool errors instead of masking them behind generic failures.
