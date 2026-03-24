<a href="https://eodhistoricaldata.com/"> <div align="center"> <picture> <source media="(prefers-color-scheme: light)" srcset="assets/icon.png"> <source media="(prefers-color-scheme: dark)" srcset="assets/icon.svg"> <img alt="EODHD logo" src="assets/icon.png" height="90"> </picture> </div> </a> <br>

# EODHD MCP Server

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

### 3) Run as an MCP sse server

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

## Using with Claude Desktop

### A) Install via MCP bundle (`.mcpb`)

1. Download the `.mcpb` from Releases (https://github.com/EodHistoricalData/EODHD-MCP-Server/releases).
2. Claude Desktop → **Settings → Extensions → Advanced → Install Extension**.
3. Select the `.mcpb`, approve, enter your API key, enable the extension.

### B) Use source checkout (developer config)

1. Clone this repo (https://github.com/EodHistoricalData/EODHD-MCP-Server) anywhere.
2. Claude Desktop → **Developer → Edit config**, add:

```json
{
  "mcpServers": {
    "eodhd-mcp": {
      "command": "python3",
      "args": [
        "/home/user/EODHD-MCP-Server/server.py", //actual path to the library
        "--stdio"
      ],
       "env": {
           "EODHD_API_KEY": "YOUR_EODHD_API_KEY" //your valid EODHD API key
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

Your MCP client will translate these into calls like:
- get_historical_stock_prices, get_fundamentals_data, get_company_news,
- get_stock_screener_data, get_technical_indicators, get_mp_us_options_contracts,
- get_mp_us_options_eod, etc.

---

### Running the built-in test clients

The tests/manual/ directory contains MCP clients that exercise the server end-to-end using the
test catalog in tests/manual/all_tests.py.

***HTTP test***

# Terminal 1: start HTTP MCP server

```bash
python -m entrypoints.server_http
# uses http://127.0.0.1:8000/mcp by default
```

# Terminal 2: run HTTP client tests

```bash
python tests/manual/test_client_http.py
# uses http://127.0.0.1:8000/mcp by default
```

***SSE test***

# Terminal 1: start SSE MCP server

```bash
python -m entrypoints.server_sse
```

# Terminal 2: run SSE client tests

```bash
python tests/manual/test_client_sse.py
```

***STDIO test***

```bash
python tests/manual/test_client_stdio.py   --cmd "python3 -m entrypoints.server_stdio --apikey YOUR_EODHD_API_KEY"
```

These clients load tests/manual/all_tests.py (plus all_tests_beta.py if you choose) which registers a comprehensive set of working calls against all the tools.

---

## MCP Tools

The tools below are implemented as separate modules under app/tools/ and registered with
the MCP server.

### Core market data

* `get_historical_stock_prices` – Daily OHLCV for a symbol and date range

* `get_intraday_historical_data` – Intraday bars (1m, 5m, 1h, etc.)

* `get_us_tick_data` – US tick-level data for equities

* `get_live_price_data` – Live (delayed) quotes

* `get_us_live_extended_quotes` – US Live v2 extended quotes

* `capture_realtime_ws` – Real-time WebSocket capture:

- us_trades (e.g. AAPL, MSFT, TSLA)

- crypto (e.g. BTC-USD, ETH-USD)

- forex (e.g. EURUSD)


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

* `get_fundamentals_data` – Fundamentals for:

    - Stocks,

    - ETFs,

    - mutual funds,

    - indices,

    - crypto,

    - FX

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

* `get_technical_indicators` – EODHD Technical Indicators API:

    - SMA, EMA

    - MACD

    - Stochastic, StochRSI

    - ATR

    - SAR

    - Beta vs index (e.g. NDX.INDX)

    - Bollinger Bands

    - Split-adjusted series

    - AmiBroker-format exports


### US options

* `get_mp_us_options_contracts` – Contracts list (filters for underlying, strike, type, expiry, pagination)

* `get_mp_us_options_eod` – EOD options data (by contract + optional filters)

* `get_mp_us_options_underlyings` – Underlying symbols list


### Indices & CBOE

* `get_mp_indices_list` – EODHD MP indices list

* `get_mp_index_components` – Components for a given index (e.g. GSPC.INDX)

* `get_cboe_indices_list` – CBOE indices listing

* `get_cboe_index_data` – CBOE index feed (e.g. snapshot_official_closing)


### illio Marketplace subscriptions data

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


### Praams Marketplace subscriptions data

* `get_mp_praams_risk_scoring_by_ticker`

* `get_mp_praams_risk_scoring_by_isin`

* `get_mp_praams_bond_analyze_by_isin`

* `get_mp_praams_bank_income_statement_by_ticker`

* `get_mp_praams_bank_income_statement_by_isin`

* `get_mp_praams_bank_balance_sheet_by_ticker`

* `get_mp_praams_bank_balance_sheet_by_isin`


### Investverte Marketplace subscriptions data

* `get_mp_investverte_esg_list_companies`

* `get_mp_investverte_esg_list_countries`

* `get_mp_investverte_esg_view_country`

* `get_mp_investverte_esg_view_company`

* `get_mp_investverte_esg_list_sectors`

* `get_mp_investverte_esg_view_sector`

For specific parameter examples and edge-case coverage, see tests/manual/all_tests.py,
which registers a wide set of “happy-path” and near-boundary calls against all tools.

---

## Project Structure

```
EODHD-MCP-Server/
├── app/
│   ├── api_client.py
│   ├── config.py
│   └── tools/
│       ├── __init__.py
│       ├── capture_realtime_ws.py
│       ├── get_cboe_index_data.py
│       ├── get_cboe_indices_list.py
│       ├── get_company_news.py
│       ├── get_earnings_trends.py
│       ├── get_economic_events.py
│       ├── get_exchange_details.py
│       ├── get_exchanges_list.py
│       ├── get_exchange_tickers.py
│       ├── get_fundamentals_data.py
│       ├── get_historical_market_cap.py
│       ├── get_historical_stock_prices.py
│       ├── get_insider_transactions.py
│       ├── get_intraday_historical_data.py
│       ├── get_live_price_data.py
│       ├── get_macro_indicator.py
│       ├── get_mp_illio_market_insights_best_worst.py
│       ├── get_mp_illio_market_insights_beta_bands.py
│       ├── get_mp_illio_market_insights_largest_volatility.py
│       ├── get_mp_illio_market_insights_performance.py
│       ├── get_mp_illio_market_insights_risk_return.py
│       ├── get_mp_illio_market_insights_volatility.py
│       ├── get_mp_illio_performance_insights.py
│       ├── get_mp_illio_risk_insights.py
│       ├── get_mp_index_components.py
│       ├── get_mp_indices_list.py
│       ├── get_mp_investverte_esg_list_companies.py
│       ├── get_mp_investverte_esg_list_countries.py
│       ├── get_mp_investverte_esg_list_sectors.py
│       ├── get_mp_investverte_esg_view_company.py
│       ├── get_mp_investverte_esg_view_country.py
│       ├── get_mp_investverte_esg_view_sector.py
│       ├── get_mp_praams_bank_balance_sheet_by_isin.py
│       ├── get_mp_praams_bank_balance_sheet_by_ticker.py
│       ├── get_mp_praams_bank_income_statement_by_isin.py
│       ├── get_mp_praams_bank_income_statement_by_ticker.py
│       ├── get_mp_praams_bond_analyze_by_isin.py
│       ├── get_mp_praams_risk_scoring_by_isin.py
│       ├── get_mp_praams_risk_scoring_by_ticker.py
│       ├── get_mp_us_options_contracts.py
│       ├── get_mp_us_options_eod.py
│       ├── get_mp_us_options_underlyings.py
│       ├── get_news_word_weights.py
│       ├── get_sentiment_data.py
│       ├── get_stock_screener_data.py
│       ├── get_stocks_from_search.py
│       ├── get_symbol_change_history.py
│       ├── get_technical_indicators.py
│       ├── get_upcoming_dividends.py
│       ├── get_upcoming_earnings.py
│       ├── get_upcoming_ipos.py
│       ├── get_upcoming_splits.py
│       ├── get_user_details.py
│       ├── get_us_live_extended_quotes.py
│       └── get_us_tick_data.py
├── assets/
│   ├── icon.png
│   └── icon.svg
├── entrypoints/
│   ├── server_http.py
│   ├── server_sse.py
│   └── server_stdio.py
├── test/
│   ├── all_tests.py
│   ├── all_tests_beta.py
│   ├── test_client_http.py
│   ├── test_client_sse.py
│   └── test_client_stdio.py
├── docker-compose.yml
├── LICENSE
├── manifest.json
├── README.md
└── server.py

```

**Entry points**

* `server.py` – convenience HTTP server entrypoint (reads `.env`).
* `entrypoints/server_http.py` – HTTP MCP server (module form).
* `entrypoints/server_sse.py` – HTTP + SSE MCP server.
* `entrypoints/server_stdio.py` – STDIO MCP server (supports `--apikey`).

---


## Privacy & Data Handling

This MCP server acts as a thin proxy between your MCP client and EODHD’s HTTP APIs.

* Your EODHD API key is used solely to authenticate requests to the EODHD API.

* The server forwards tool requests to EODHD and returns responses to your MCP client.

* The server does not persist or cache your prompts or EODHD responses by default.

* All data handling and retention are ultimately governed by EODHD’s own policies and your subscription plan.

Please refer to EODHD’s official privacy policy for details: [EODHD Privacy Policy](https://eodhd.com/financial-apis/privacy-policy)

By using this MCP server, you agree that any data fetched through it is subject to EODHD’s privacy policy and terms of service.


## License

This project is licensed under the MIT License. See LICENSE for details.


## Contributing

Contributions are welcome:

Open an issue for bugs, questions or feature requests.

If you plan a larger change (new tools, new Marketplace integration, etc.), please describe
your approach in the issue first.

Add or update tests in tests/manual/all_tests.py (and optionally all_tests_beta.py) to cover
new behavior.

Run the HTTP / SSE / STDIO test clients to ensure everything passes.

Submit a PR referencing the related issue.

Bug reports that include logs, tool parameters, and clear reproduction steps are especially
helpful.
