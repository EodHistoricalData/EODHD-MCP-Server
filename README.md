<a href="https://eodhd.com/"> <div align="center"> <picture> <source media="(prefers-color-scheme: light)" srcset="assets/icon.png"> <source media="(prefers-color-scheme: dark)" srcset="assets/icon.svg"> <img alt="EODHD logo" src="assets/icon.png" height="90"> </picture> </div> </a> <br>

# EODHD MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/EodHistoricalData/EODHD-MCP-Server/actions/workflows/ci.yml/badge.svg)](https://github.com/EodHistoricalData/EODHD-MCP-Server/actions)

A Model Context Protocol (MCP) server that exposes the [EOD Historical Data](https://eodhd.com/) (EODHD) APIs to MCP-compatible clients (Claude Desktop, Claude Code, ChatGPT MCP/Connectors, MCP Inspector, custom agents, etc.).

It provides tool-based access to:

### Main subscriptions datasets:

* End-of-day, intraday & tick data
* Live (delayed) quotes & US Live v2 extended quotes
* Fundamentals, earnings & financials
* News, sentiment & news word weights
* Stock screener & discovery endpoints
* Corporate actions (dividends, splits, IPOs)
* Macro indicators, exchanges & listings
* CBOE indices and feeds

### Marketplace datasets:

* Options (contracts, EOD, underlying symbols)
* illio (performance, risk & market insights)
* Praams (risk scoring, bonds, banks)
* Investverte ESG (companies, countries, sectors)


## Highlights

✅ End-of-day, intraday, and US tick data

✅ Live (delayed) quotes and extended US quotes (Live v2)

✅ Fundamentals (stocks, ETFs, mutual funds, indices, crypto, FX)

✅ Earnings, IPOs, splits, dividends & symbol changes

✅ News, sentiment and topic/word weights

✅ Screeners & technical indicators (SMA, EMA, MACD, Stoch, BBands, etc.)

✅ US options (contracts, EOD, underlyings)

✅ Macro indicators, economic events, exchanges & tickers

✅ Marketplace tools (illio, Praams, Investverte ESG, CBOE)

✅ **NEW:** ESG data, analyst ratings, institutional holders

✅ **NEW:** Bulk data APIs, ID mapping (CUSIP/ISIN/FIGI)

✅ **NEW:** Batch operations, data export (CSV/JSON)

✅ **NEW:** Docker support, Prometheus metrics, health endpoints

✅ **NEW (v2.6.1):** Redis cache, structured JSON logging, pre-commit hooks

✅ **NEW (v2.6.1):** Jupyter notebook examples for portfolio analysis


## Requirements

* Python **3.10+**
* A valid EODHD API key (set via EODHD_API_KEY or --apikey)
* An MCP-compatible client, for example:
    - Claude Desktop / Claude Code
    - ChatGPT with MCP / Connectors
    - MCP Inspector
    - Custom MCP client


## Installation & Setup

### 1) Clone & install

```bash
git clone https://github.com/EodHistoricalData/EODHD-MCP-Server.git
cd EODHD-MCP-Server
pip install -r requirements.txt
```

Create a `.env` at the repo root (used by HTTP + stdio entrypoints):

```env
EODHD_API_KEY=YOUR_EODHD_API_KEY
# Optional (HTTP server):
MCP_HOST=127.0.0.1
MCP_PORT=8000
```

---

### 2) Run as a local HTTP server

**Option A (root entrypoint):**

```bash
python server.py
# → http://127.0.0.1:8000/mcp (defaults; override with MCP_HOST/MCP_PORT)
```

**Option B (module entrypoint):**

```bash
python -m entrypoints.server_http
# uses .env for key/host/port
```

---

### 3) Run as an MCP SSE server

```bash
python -m entrypoints.server_sse
```

---

### 4) Run as an MCP stdio server

For clients that launch the server via stdio:

```bash
# Pass API key from CLI, useful for dev or when no .env
python -m entrypoints.server_stdio --apikey YOUR_EODHD_API_KEY
```

(If `--apikey` is set, it overrides `EODHD_API_KEY` from the environment.)

---

## Docker Deployment

### Quick Start with Docker

```bash
# Build and run
docker-compose up -d

# Or build manually
docker build -t eodhd-mcp-server .
docker run -d -p 8000:8000 -e EODHD_API_KEY=your_api_key eodhd-mcp-server
```

### Docker Compose (Recommended)

Create a `.env` file:
```env
EODHD_API_KEY=your_api_key_here
```

Run:
```bash
docker-compose up -d
```

The server will be available at `http://localhost:8000/mcp`

### Docker Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EODHD_API_KEY` | `demo` | Your EODHD API key |
| `MCP_HOST` | `0.0.0.0` | Server host |
| `MCP_PORT` | `8000` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level |

### Health Check

```bash
curl http://localhost:8000/health
```

---

## Using with Claude Desktop

### A) Install via MCP bundle (`.mcpb`)

1. Download the `.mcpb` from [Releases](https://github.com/EodHistoricalData/EODHD-MCP-Server/releases).
2. Claude Desktop → **Settings → Extensions → Advanced → Install Extension**.
3. Select the `.mcpb`, approve, enter your API key, enable the extension.

### B) Use source checkout (developer config)

1. Clone this repo anywhere.
2. Claude Desktop → **Developer → Edit config**, add:

```json
{
  "mcpServers": {
    "eodhd-mcp": {
      "command": "python3",
      "args": [
        "/path/to/EODHD-MCP-Server/server.py",
        "--stdio"
      ],
       "env": {
           "EODHD_API_KEY": "YOUR_EODHD_API_KEY"
         }
    }
  }
}
```

Restart Claude Desktop. The server will be launched on demand via stdio.

---

## Using with ChatGPT (beta MCP support)

1. Open ChatGPT **Settings** → ensure your plan supports **Connectors / MCP**.
2. Enable developer/connectors features.
3. Add a custom MCP **HTTP** source:
   * URL: `http://127.0.0.1:8000/mcp` (or your deployed URL)
   * Provide your EODHD API key as required by your gateway or set it in `.env` on the server.
4. Start a new chat → **Add sources** → select your MCP server.

> If your ChatGPT workspace supports hosted connectors with query params, you can deploy the HTTP server and expose a URL like:
> `https://YOUR_HOST/mcp` (API key handled server-side via env).

---

## Usage Examples

Below are concrete examples showing how to use the server with natural language prompts (Claude / ChatGPT)

### Example 1

Once the MCP server is registered in your client (Claude Desktop, Claude Code, ChatGPT MCP, etc.), you can simply ask:

* Get daily OHLCV data for AAPL.US between 2023-01-01 and 2023-02-28 using the EODHD MCP tools and summarize the price trend.

### Example 2

* Use the EODHD MCP server to:
1) Fetch full fundamentals for AAPL.US (including financials),
2) Pull the latest company news for AAPL.US,
3) Summarize how recent news aligns with the fundamentals.

### Example 3

* Ask the EODHD MCP tools to:
    - Screen US technology stocks with market capitalization > 10B,
    - Compute 30-day SMA and MACD for AAPL.US in mid-2022,
    - List a few AAPL.US options contracts and show EOD data for one of them.

### Example 4 (New in v2.6)

* Use batch operations:
    - Get quotes for AAPL.US, MSFT.US, GOOGL.US, AMZN.US at once
    - Compare these stocks side by side
    - Export the comparison to CSV format

Your MCP client will translate these into calls like:
- get_historical_stock_prices, get_fundamentals_data, get_company_news,
- get_stock_screener_data, get_technical_indicators, get_mp_us_options_contracts,
- batch_quotes, compare_stocks, export_data, etc.

---

## CLI Utilities

Quick command-line tools for testing:

```bash
# Validate API key
python cli.py check

# Get stock quote
python cli.py quote AAPL.US

# Search for stocks
python cli.py search microsoft

# Get price history
python cli.py history TSLA.US

# List all exchanges
python cli.py exchanges

# List available tools
python cli.py tools
```

---

## Running the built-in test clients

The test/ directory contains MCP clients that exercise the server end-to-end using the
test catalog in test/all_tests.py.

**HTTP test**

```bash
# Terminal 1: start HTTP MCP server
python -m entrypoints.server_http
# uses http://127.0.0.1:8000/mcp by default

# Terminal 2: run HTTP client tests
python test/test_client_http.py
```

**SSE test**

```bash
# Terminal 1: start SSE MCP server
python -m entrypoints.server_sse

# Terminal 2: run SSE client tests
python test/test_client_sse.py
```

**STDIO test**

```bash
python test/test_client_stdio.py --cmd "python3 -m entrypoints.server_stdio --apikey YOUR_EODHD_API_KEY"
```

**Pytest Suite**

```bash
# Install dev dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

---

## MCP Tools

The tools below are implemented as separate modules under app/tools/ and registered with
the MCP server. **Total: 75 tools**

### Core market data

* `get_historical_stock_prices` – Daily OHLCV for a symbol and date range
* `get_intraday_historical_data` – Intraday bars (1m, 5m, 1h, etc.)
* `get_us_tick_data` – US tick-level data for equities
* `get_live_price_data` – Live (delayed) quotes
* `get_us_live_extended_quotes` – US Live v2 extended quotes
* `capture_realtime_ws` – Real-time WebSocket capture (us_trades, crypto, forex)

### Bulk & Batch Data (NEW)

* `get_bulk_eod` – Bulk EOD/Splits/Dividends for entire exchange
* `get_bulk_fundamentals` – Bulk fundamentals for multiple symbols
* `batch_quotes` – Batch quotes for multiple symbols at once
* `compare_stocks` – Side-by-side stock comparison

### Advanced Analytics (NEW)

* `get_esg_data` – ESG (Environmental, Social, Governance) scores
* `get_analyst_ratings` – Wall Street analyst ratings and price targets
* `get_institutional_holders` – Major institutional investors
* `get_insider_summary` – Aggregated insider trading summary
* `get_short_interest` – Short interest data and metrics
* `get_financial_ratios` – Comprehensive financial ratios

### Reference Data (NEW)

* `get_id_mapping` – Convert CUSIP/ISIN/FIGI/LEI/CIK to Symbol
* `get_historical_constituents` – Historical index composition
* `get_market_status` – Market open/closed status
* `get_delisted_stocks` – Delisted companies data
* `get_stock_logo` – Company logo URLs
* `get_forex_list` – Available forex pairs
* `get_crypto_list` – Available cryptocurrencies
* `get_bonds_data` – Bond information by ISIN/CUSIP

### Sector & Comparison (NEW)

* `get_sector_performance` – Performance data by market sector
* `get_stock_peers` – Find similar companies for comparison
* `get_historical_dividends` – Complete dividend history with analytics
* `export_data` – Export data in CSV/JSON format

### News, sentiment, discovery

* `get_company_news` – Company/ticker-based news
* `get_sentiment_data` – News sentiment for one or more symbols
* `get_news_word_weights` – Weighted news keywords over a date window
* `get_stocks_from_search` – Search companies/bonds by ticker, name, ISIN, etc.
* `get_stock_screener_data` – EODHD Stock Screener wrapper (filters, signals, sorting)

### Exchanges & reference data

* `get_exchanges_list` – List all exchanges
* `get_exchange_tickers` – Tickers for a given exchange (and optional type)
* `get_exchange_details` – Trading hours, holidays, etc. per exchange
* `get_symbol_change_history` – Symbol / code change history

### Fundamentals, macro & user details

* `get_fundamentals_data` – Fundamentals for stocks, ETFs, mutual funds, indices, crypto, FX
* `get_historical_market_cap` – Historical market cap series
* `get_macro_indicator` – Macro indicators (GDP, CPI, etc.)
* `get_economic_events` – Economic events, including filters (comparison, type)
* `get_user_details` – Account and quota/usage info
* `get_insider_transactions` – Insider transaction data (with symbol and window filters)

### Calendars & corporate actions

* `get_upcoming_earnings` – Earnings calendar (by date or symbol list)
* `get_earnings_trends` – Earnings trends for one or more tickers
* `get_upcoming_ipos` – Upcoming IPOs
* `get_upcoming_splits` – Upcoming stock splits
* `get_upcoming_dividends` – Upcoming dividends (by symbol, by date, or by window)

### Technical indicators

* `get_technical_indicators` – EODHD Technical Indicators API: SMA, EMA, MACD, Stochastic, StochRSI, ATR, SAR, Beta, Bollinger Bands

### US options

* `get_mp_us_options_contracts` – Contracts list (filters for underlying, strike, type, expiry, pagination)
* `get_mp_us_options_eod` – EOD options data (by contract + optional filters)
* `get_mp_us_options_underlyings` – Underlying symbols list

### Indices & CBOE

* `get_mp_indices_list` – EODHD MP indices list
* `get_mp_index_components` – Components for a given index (e.g. GSPC.INDX)
* `get_cboe_indices_list` – CBOE indices listing
* `get_cboe_index_data` – CBOE index feed (e.g. snapshot_official_closing)

### illio Marketplace

* `get_mp_illio_performance_insights`
* `get_mp_illio_risk_insights`
* `get_mp_illio_market_insights_performance`
* `get_mp_illio_market_insights_best_worst`
* `get_mp_illio_market_insights_volatility`
* `get_mp_illio_market_insights_risk_return`
* `get_mp_illio_market_insights_largest_volatility`
* `get_mp_illio_market_insights_beta_bands`

These tools support canonical IDs like SnP500, dow, nasdaq100, NDX, spx, etc.
where the server normalizes aliases to the correct index.

### Praams Marketplace

* `get_mp_praams_risk_scoring_by_ticker`
* `get_mp_praams_risk_scoring_by_isin`
* `get_mp_praams_bond_analyze_by_isin`
* `get_mp_praams_bank_income_statement_by_ticker`
* `get_mp_praams_bank_income_statement_by_isin`
* `get_mp_praams_bank_balance_sheet_by_ticker`
* `get_mp_praams_bank_balance_sheet_by_isin`

### Investverte ESG Marketplace

* `get_mp_investverte_esg_list_companies`
* `get_mp_investverte_esg_list_countries`
* `get_mp_investverte_esg_view_country`
* `get_mp_investverte_esg_view_company`
* `get_mp_investverte_esg_list_sectors`
* `get_mp_investverte_esg_view_sector`

For specific parameter examples and edge-case coverage, see test/all_tests.py,
which registers a wide set of "happy-path" and near-boundary calls against all tools.

---

## Project Structure

```
EODHD-MCP-Server/
├── app/
│   ├── api_client.py      # HTTP client with retry logic
│   ├── batch.py           # Batch request processing
│   ├── cache.py           # In-memory LRU caching
│   ├── config.py          # Configuration
│   ├── export.py          # Data export utilities
│   ├── health.py          # Health check endpoints
│   ├── metrics.py         # Prometheus metrics
│   ├── models.py          # Pydantic models
│   ├── utils.py           # Common utilities
│   └── tools/             # 75 API tool modules
├── entrypoints/
│   ├── server_http.py     # HTTP server
│   ├── server_sse.py      # SSE server
│   └── server_stdio.py    # STDIO server
├── tests/                 # Pytest test suite
├── test/                  # Integration test clients
├── .github/workflows/     # GitHub Actions CI
├── assets/                # Logo files
├── server.py              # Main entry point
├── cli.py                 # CLI utilities
├── Dockerfile             # Docker image
├── docker-compose.yml     # Docker Compose
├── manifest.json          # MCP manifest
├── requirements.txt       # Python dependencies
├── CHANGELOG.md           # Version history
└── README.md              # This file
```

**Entry points**

* `server.py` – convenience HTTP server entrypoint (reads `.env`).
* `entrypoints/server_http.py` – HTTP MCP server (module form).
* `entrypoints/server_sse.py` – HTTP + SSE MCP server.
* `entrypoints/server_stdio.py` – STDIO MCP server (supports `--apikey`).

---

## What's New in v2.6.0

### New Features
- **22 new API tools**: Bulk data, ID mapping, ESG, analyst ratings, sector performance, batch operations, data export, and more
- **Prometheus metrics**: Request tracking, cache stats, rate limits
- **Health endpoints**: `/health/live`, `/health/ready`, `/health/status`
- **Batch operations**: Parallel requests for multiple symbols
- **Data export**: CSV/JSON export with metadata
- **In-memory caching**: LRU cache with TTL support
- **Pydantic models**: Type-safe response validation

### Infrastructure
- **Docker support**: Dockerfile, docker-compose.yml with health checks
- **GitHub Actions CI**: Linting, testing, security scanning
- **CLI utilities**: Quick testing and debugging tools

See [CHANGELOG.md](CHANGELOG.md) for full details.

---

## Privacy & Data Handling

This MCP server acts as a thin proxy between your MCP client and EODHD's HTTP APIs.

* Your EODHD API key is used solely to authenticate requests to the EODHD API.
* The server forwards tool requests to EODHD and returns responses to your MCP client.
* The server does not persist or cache your prompts or EODHD responses by default.
* All data handling and retention are ultimately governed by EODHD's own policies and your subscription plan.

Please refer to EODHD's official privacy policy for details: [EODHD Privacy Policy](https://eodhd.com/financial-apis/privacy-policy)

By using this MCP server, you agree that any data fetched through it is subject to EODHD's privacy policy and terms of service.


## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.


## Contributing

Contributions are welcome:

1. Open an issue for bugs, questions or feature requests.
2. If you plan a larger change (new tools, new Marketplace integration, etc.), please describe your approach in the issue first.
3. Add or update tests in test/all_tests.py to cover new behavior.
4. Run the HTTP / SSE / STDIO test clients to ensure everything passes.
5. Submit a PR referencing the related issue.

Bug reports that include logs, tool parameters, and clear reproduction steps are especially helpful.


## Support

- **EODHD API Issues**: [support@eodhistoricaldata.com](mailto:support@eodhistoricaldata.com)
- **MCP Server Issues**: [GitHub Issues](https://github.com/EodHistoricalData/EODHD-MCP-Server/issues)
- **API Documentation**: [eodhd.com/financial-apis](https://eodhd.com/financial-apis/)

---

<div align="center">
<b>Powered by <a href="https://eodhd.com/">EODHD</a> - Financial Data APIs</b>
</div>
