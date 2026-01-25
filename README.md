<a href="https://eodhd.com/"> <div align="center"> <picture> <source media="(prefers-color-scheme: light)" srcset="assets/icon.png"> <source media="(prefers-color-scheme: dark)" srcset="assets/icon.svg"> <img alt="EODHD logo" src="assets/icon.png" height="90"> </picture> </div> </a> <br>

# EODHD MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/EodHistoricalData/EODHD-MCP-Server/actions/workflows/ci.yml/badge.svg)](https://github.com/EodHistoricalData/EODHD-MCP-Server/actions)

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides AI assistants (Claude, ChatGPT, etc.) access to **[EODHD](https://eodhd.com/)** financial market data APIs.

---

## Quick Links

| Resource | Link |
|----------|------|
| **EODHD Website** | [eodhd.com](https://eodhd.com/) |
| **API Documentation** | [eodhd.com/financial-apis](https://eodhd.com/financial-apis/) |
| **Get API Key** | [eodhd.com/register](https://eodhd.com/register) |
| **Pricing Plans** | [eodhd.com/pricing](https://eodhd.com/pricing) |
| **API Support** | [support@eodhistoricaldata.com](mailto:support@eodhistoricaldata.com) |

---

## Requirements & Limitations

### Requirements

- **Python 3.10+**
- **EODHD API Key** - [Get one here](https://eodhd.com/register)
- **MCP-compatible client**: Claude Desktop, Claude Code, ChatGPT with MCP, etc.

### API Limitations

| Plan | API Calls/Day | Data Access |
|------|---------------|-------------|
| **Free** | 20 | EOD data for last year only |
| **Basic ($19.99/mo)** | 100,000 | Full historical data |
| **Professional** | Unlimited | All data + Fundamentals |

**Rate Limits**: The server includes automatic rate limiting (100ms between requests) and retry logic.

**Data Coverage**: 150,000+ tickers across 70+ exchanges worldwide.

For full pricing details, visit [eodhd.com/pricing](https://eodhd.com/pricing).

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/EodHistoricalData/EODHD-MCP-Server.git
cd EODHD-MCP-Server
pip install -r requirements.txt
```

### 2. Configure API Key

Create a `.env` file in the project root:

```env
EODHD_API_KEY=your_api_key_here
```

Or set environment variable:

```bash
export EODHD_API_KEY=your_api_key_here
```

### 3. Run the Server

**HTTP Server (recommended for testing):**
```bash
python server.py
# Server runs at http://127.0.0.1:8000/mcp
```

**STDIO Server (for Claude Desktop):**
```bash
python -m entrypoints.server_stdio --apikey YOUR_API_KEY
```

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

## Integration with AI Clients

### Claude Desktop

1. Open Claude Desktop -> **Settings** -> **Developer** -> **Edit Config**

2. Add this configuration:

```json
{
  "mcpServers": {
    "eodhd": {
      "command": "python3",
      "args": [
        "/path/to/EODHD-MCP-Server/server.py",
        "--stdio"
      ],
      "env": {
        "EODHD_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

3. Restart Claude Desktop

### Claude Code (CLI)

```bash
cd /path/to/EODHD-MCP-Server
export EODHD_API_KEY=your_api_key
claude
```

### ChatGPT with MCP

1. Start the HTTP server: `python server.py`
2. In ChatGPT, add MCP source: `http://127.0.0.1:8000/mcp`

---

## Available Tools (75 total)

### Core Market Data
| Tool | Description |
|------|-------------|
| `get_historical_stock_prices` | End-of-day OHLCV data |
| `get_live_price_data` | Live (delayed) quotes |
| `get_intraday_historical_data` | Intraday bars (1m, 5m, 1h) |
| `get_us_tick_data` | US tick-level data |
| `get_us_live_extended_quotes` | US Live v2 extended quotes |
| `capture_realtime_ws` | Real-time WebSocket data |

### Bulk Data
| Tool | Description |
|------|-------------|
| `get_bulk_eod` | Bulk EOD/Splits/Dividends for entire exchange |
| `get_bulk_fundamentals` | Bulk fundamentals for multiple symbols |

### Fundamentals & Reference
| Tool | Description |
|------|-------------|
| `get_fundamentals_data` | Full fundamentals (stocks, ETFs, funds, crypto) |
| `get_historical_market_cap` | Historical market capitalization |
| `get_stock_logo` | Company logo URLs |
| `get_delisted_stocks` | Delisted companies data |
| `get_financial_ratios` | Comprehensive financial ratios |

### Advanced Analytics
| Tool | Description |
|------|-------------|
| `get_esg_data` | ESG scores (Environmental, Social, Governance) |
| `get_analyst_ratings` | Wall Street analyst ratings and price targets |
| `get_institutional_holders` | Major institutional investors |
| `get_insider_summary` | Aggregated insider trading summary |
| `get_short_interest` | Short interest data and metrics |

### Sector & Comparison
| Tool | Description |
|------|-------------|
| `get_sector_performance` | Performance data by market sector |
| `get_stock_peers` | Find similar companies for comparison |
| `get_historical_dividends` | Complete dividend history with analytics |
| `compare_stocks` | Side-by-side stock comparison |

### Batch Operations
| Tool | Description |
|------|-------------|
| `batch_quotes` | Get quotes for multiple symbols at once |

### Data Export
| Tool | Description |
|------|-------------|
| `export_data` | Export data in CSV/JSON format |

### ID Mapping
| Tool | Description |
|------|-------------|
| `get_id_mapping` | Convert CUSIP/ISIN/FIGI/LEI/CIK to Symbol |

### News & Sentiment
| Tool | Description |
|------|-------------|
| `get_company_news` | Company news articles |
| `get_sentiment_data` | News sentiment scores |
| `get_news_word_weights` | Topic/keyword analysis |

### Exchanges & Listings
| Tool | Description |
|------|-------------|
| `get_exchanges_list` | List of all exchanges |
| `get_exchange_tickers` | Tickers for an exchange |
| `get_exchange_details` | Trading hours, holidays |
| `get_market_status` | Market open/closed status |
| `get_forex_list` | Available forex pairs |
| `get_crypto_list` | Available cryptocurrencies |

### Calendar & Corporate Actions
| Tool | Description |
|------|-------------|
| `get_upcoming_earnings` | Earnings calendar |
| `get_earnings_trends` | Earnings trends |
| `get_upcoming_ipos` | IPO calendar |
| `get_upcoming_splits` | Stock splits |
| `get_upcoming_dividends` | Dividends calendar |
| `get_insider_transactions` | Insider transactions |

### Technical Analysis
| Tool | Description |
|------|-------------|
| `get_technical_indicators` | SMA, EMA, MACD, RSI, BBands, etc. |
| `get_stock_screener_data` | Stock screener with filters |

### Options (Marketplace)
| Tool | Description |
|------|-------------|
| `get_mp_us_options_contracts` | Options contracts |
| `get_mp_us_options_eod` | Options EOD data |
| `get_mp_us_options_underlyings` | Underlying symbols |

### Indices
| Tool | Description |
|------|-------------|
| `get_mp_indices_list` | List of indices |
| `get_mp_index_components` | Index constituents |
| `get_historical_constituents` | Historical index composition |
| `get_cboe_indices_list` | CBOE indices |
| `get_cboe_index_data` | CBOE index data |

### Marketplace: illio
Performance and risk insights for major indices (S&P 500, Dow Jones, NASDAQ 100).

### Marketplace: Praams
Risk scoring, bond analysis, bank financials.

### Marketplace: Investverte ESG
ESG data for companies, countries, and sectors.

---

## Usage Examples

Once connected, ask your AI assistant:

```
"Get daily prices for AAPL.US from January to March 2024"

"Show me the fundamentals for Microsoft including financials"

"What's the current sentiment for Tesla stock?"

"Screen US tech stocks with market cap over 10 billion"

"Get the S&P 500 index constituents"

"Convert ISIN US0378331005 to ticker symbol"
```

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

## Testing

### Quick Tests

```bash
# Terminal 1: Start server
python server.py

# Terminal 2: Run HTTP tests
python test/test_client_http.py
```

### Pytest Suite

```bash
# Install dev dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Code Quality

```bash
# Linting
pip install ruff
ruff check .

# Type checking
pip install mypy
mypy app/
```

---

## Project Structure

```
EODHD-MCP-Server/
├── app/
│   ├── api_client.py      # HTTP client with retry logic
│   ├── batch.py           # Batch request processing
│   ├── cache.py           # In-memory caching
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
├── test/                  # Integration tests
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

---

## What's New in v2.6.0

### New Features
- **17 new API tools**: Bulk data, ID mapping, ESG, analyst ratings, sector performance, batch operations, data export, and more
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

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

---

## Support

- **EODHD API Issues**: [support@eodhistoricaldata.com](mailto:support@eodhistoricaldata.com)
- **MCP Server Issues**: [GitHub Issues](https://github.com/EodHistoricalData/EODHD-MCP-Server/issues)
- **API Documentation**: [eodhd.com/financial-apis](https://eodhd.com/financial-apis/)

---

<div align="center">
<b>Powered by <a href="https://eodhd.com/">EODHD</a> - Financial Data APIs</b>
</div>
