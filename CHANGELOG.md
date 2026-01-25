# Changelog

All notable changes to the EODHD MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.6.0] - 2025-01-25

### Added

- **New API Tools (17):**
  - `get_esg_data` - ESG (Environmental, Social, Governance) scores
  - `get_analyst_ratings` - Wall Street analyst ratings and price targets
  - `get_institutional_holders` - Major institutional investors
  - `get_insider_summary` - Aggregated insider trading summary
  - `get_short_interest` - Short interest data and metrics
  - `get_financial_ratios` - Comprehensive financial ratios
  - `get_bulk_eod` - Bulk EOD data for entire exchange
  - `get_id_mapping` - Convert CUSIP/ISIN/FIGI/LEI/CIK to Symbol
  - `get_historical_constituents` - Historical index composition
  - `get_market_status` - Market open/closed status
  - `get_delisted_stocks` - Delisted companies data
  - `get_stock_logo` - Company logo URLs
  - `get_forex_list` - Available forex pairs
  - `get_crypto_list` - Available cryptocurrencies
  - `get_bonds_data` - Bond information by ISIN/CUSIP
  - `get_bulk_fundamentals` - Bulk fundamentals for multiple symbols
  - `get_sector_performance` - Performance data by market sector
  - `get_stock_peers` - Find similar companies for comparison
  - `get_historical_dividends` - Complete dividend history with analytics
  - `batch_quotes` - Batch quotes for multiple symbols
  - `compare_stocks` - Side-by-side stock comparison
  - `export_data` - Export data in CSV/JSON format

- **Core Infrastructure:**
  - `app/utils.py` - Common utilities (error handling, validation, formatting)
  - `app/cache.py` - In-memory LRU cache with TTL support
  - `app/models.py` - Pydantic models for type-safe responses
  - `app/metrics.py` - Prometheus-compatible metrics
  - `app/health.py` - Health check endpoints (liveness, readiness, status)
  - `app/batch.py` - Parallel request processing
  - `app/export.py` - Data export utilities (CSV, JSON)

- **Developer Experience:**
  - `cli.py` - Command-line utilities (check, quote, search, history, exchanges, tools)
  - `requirements.txt` - Python dependencies file
  - `tests/` - Comprehensive pytest test suite (8 test modules)
  - `.github/workflows/ci.yml` - GitHub Actions CI/CD pipeline

- **Docker Support:**
  - `Dockerfile` - Multi-stage Docker image (Python 3.11 slim)
  - `docker-compose.yml` - Full Docker Compose setup with health checks
  - `.dockerignore` - Optimized build context

### Changed

- Total tools now: 75 (was 56)
- Updated README with comprehensive documentation
- Added API rate limiting information
- Improved project structure documentation

## [2.3.4] - 2024-12-12

### Initial Release

- 56 API tools for EODHD financial data
- Support for HTTP, SSE, and STDIO transports
- Core market data (EOD, intraday, live quotes)
- Fundamentals data (stocks, ETFs, funds, crypto)
- News and sentiment analysis
- Technical indicators
- Options data (contracts, EOD, underlyings)
- Marketplace integrations (illio, Praams, Investverte ESG)
- CBOE indices support
- Comprehensive test suite
