# This module registers all test cases in one place.
# It's possible to split it into multiple files later (e.g. tests/eod.py, tests/news.py)
# and add them to TEST_MODULES in test client (test_client_http.py, test_client_sse.py etc.

def register(add_test, COMMON):

    # --- Intraday ---
    add_test({
        "name": "Intraday: 1m range",
        "tool": "get_intraday_historical_data",
        "use_common": ["fmt", "api_token", "ticker"],
        "params": {
            #"ticker": "AAPL.US",
            "interval": "1m",
            "from_timestamp": 1627896900,  # 2021-08-02 09:35:00 UTC
            "to_timestamp": 1628069700,    # 2021-08-04 09:35:00 UTC
            "split_dt": False,
        },
    })

    # --- Intraday: near-max ranges with mixed date formats ---

    # 1) 1m — ~119 days (max is 120) using Unix timestamps
    add_test({
        "name": "Intraday: 1m near-max (timestamps)",
        "tool": "get_intraday_historical_data",
        "use_common": ["fmt", "api_token", "ticker"],
        "params": {
            # 2021-01-01 00:00:00 UTC -> 2021-04-30 00:00:00 UTC  (119 days)
            "interval": "1m",
            "from_timestamp": 1609459200,  # 2021-01-01
            "to_timestamp": 1619740800,  # 2021-04-30
            "split_dt": False,
        },
    })


    # 2) 5m — 599 days (max is 600) using DD-MM-YYYY
    add_test({
        "name": "Intraday: 5m near-max (DD-MM-YYYY)",
        "tool": "get_intraday_historical_data",
        "use_common": ["fmt", "api_token", "ticker"],
        "params": {
            # 01-01-2020 -> 22-08-2021 (599 days)
            "interval": "5m",
            "from_timestamp": "01-01-2020",
            "to_timestamp": "22-08-2021",
            "split_dt": True,
        },
    })

    # 3) 5m — 599 days (max is 600) using YYYY/MM/DD
    add_test({
        "name": "Intraday: 5m near-max (YYYY/MM/DD)",
        "tool": "get_intraday_historical_data",
        "use_common": ["fmt", "api_token", "ticker"],
        "params": {
            # 2020/01/01 -> 2021/08/22 (599 days)
            "interval": "5m",
            "from_timestamp": "2020/01/01",
            "to_timestamp": "2021/08/22",
            "split_dt": False,
        },
    })

    # 4) 1h — 7199 days (max is 7200) using mixed natural + ISO-8601
    add_test({
        "name": "Intraday: 1h near-max (natural + ISO8601)",
        "tool": "get_intraday_historical_data",
        "use_common": ["fmt", "api_token", "ticker"],
        "params": {
            # "Jan 1, 2010" -> "2029-09-17T00:00:00Z" (7199 days)
            "interval": "1h",
            "from_timestamp": "Jan 1, 2010",
            "to_timestamp": "2029-09-17T00:00:00Z",
            "split_dt": False,
        },
    })

    # --- Intraday: 1m near-max, DD-MM-YYYY date strings (≈119 days < 120 max) ---
    add_test({
        "name": "Intraday: 1m near-max (DD-MM-YYYY)",
        "tool": "get_intraday_historical_data",
        "use_common": ["fmt", "api_token", "ticker"],
        "params": {
            # "ticker": "AAPL.US",
            "interval": "1m",
            "from_timestamp": "01-11-2024",  # DD-MM-YYYY
            "to_timestamp": "28-02-2025",  # DD-MM-YYYY
            "split_dt": False,
        },
    })

    # --- Intraday: 1h near-max, DD-MM-YYYY date strings (7199 days < 7200 max) ---
    add_test({
        "name": "Intraday: 1h near-max (DD-MM-YYYY)",
        "tool": "get_intraday_historical_data",
        "use_common": ["fmt", "api_token", "ticker"],
        "params": {
            # "ticker": "AAPL.US",
            "interval": "1h",
            "from_timestamp": "01-01-2010",  # DD-MM-YYYY
            "to_timestamp": "17-09-2029",  # DD-MM-YYYY
            "split_dt": False,
        },
    })

    # --- End of Day API ---
    add_test({
        "name": "EOD: AAPL Jan-Feb 2023",
        "tool": "get_historical_stock_prices",
        "use_common": ["api_token", "fmt", "start_date", "end_date", "ticker"],
        "params": {
            # "ticker": "AAPL.US",

        },
    })

    # --- Live (Delayed) ---
    add_test({
        "name": "Live: AAPL + extras",
        "tool": "get_live_price_data",
        "use_common": ["fmt", "api_token", "ticker"],  # token optional; env works
        "params": {
            # "ticker": "AAPL.US",
            "additional_symbols": ["VTI", "EUR.FOREX"],
        },
    })

    # --- News by ticker ---
    add_test({
        "name": "News: by ticker AAPL",
        "tool": "get_company_news",
        "use_common": ["fmt", "api_token"],
        "params": {
            "ticker": "AAPL.US",
            "limit": 5,
            "offset": 0,
        },
    })

    # --- News by tag ---
    add_test({
        "name": "News: by tag AI",
        "tool": "get_company_news",
        "use_common": ["fmt", "api_token", "limit", "offset"],
        "params": {
            "tag": "ARTIFICIAL INTELLIGENCE",

        },
    })

    # --- Sentiment ---
    add_test({
        "name": "Sentiment: BTC + AAPL Q1 2022",
        "tool": "get_sentiment_data",
        "use_common": ["fmt", "start_date", "end_date", "api_token"],
        "params": {
            "symbols": "BTC-USD.CC,AAPL.US",

        },
    })

    # --- News Word Weights ---
    add_test({
        "name": "News Word Weights: AAPL top 10 words",
        "tool": "get_news_word_weights",
        "use_common": ["fmt", "api_token"],
        "params": {
            "ticker": "AAPL.US",
            "start_date": "2025-04-08",
            "end_date": "2025-04-16",
            "limit": 10,
        },
    })

    # --- Search ---
    add_test({
        "name": "Search: by ticker",
        "tool": "get_stocks_from_search",
        "use_common": ["fmt", "api_token"],
        "params": {
            "query": "AAPL",
            "limit": 10,
            # "api_token": "demo",  # NOTE: Demo won't work for Search API in prod; override as needed
        },
    })
    add_test({
        "name": "Search: by name (filtered US stock)",
        "tool": "get_stocks_from_search",
        "use_common": ["fmt", "api_token"],
        "params": {
            "query": "Apple Inc",
            "limit": 5,
            "exchange": "US",
            "type": "stock",
            # "api_token": "demo",  # replace with real token
        },
    })
    add_test({
        "name": "Search: bonds-only ISIN",
        "tool": "get_stocks_from_search",
        "use_common": ["fmt", "api_token"],
        "params": {
            "query": "US0378331005",
            "limit": 3,
            "bonds_only": True,
            # "api_token": "demo",  # replace with real token
        },
    })

    # --- Exchanges list / tickers / details ---
    add_test({
        "name": "Exchanges: list",
        "tool": "get_exchanges_list",
        "use_common": ["fmt", "api_token"],
        "params": {},
    })
    add_test({
        "name": "Exchange tickers: US unified",
        "tool": "get_exchange_tickers",
        "use_common": ["fmt", "api_token"],
        "params": {
            "exchange_code": "US",
        },
    })
    add_test({
        "name": "Exchange tickers: WAR stock",
        "tool": "get_exchange_tickers",
        "use_common": ["fmt", "api_token"],
        "params": {
            "exchange_code": "WAR",
            "type": "stock",
        },
    })
    add_test({
        "name": "Exchange details: US (default window)",
        "tool": "get_exchange_details",
        "use_common": ["fmt", "api_token"],
        "params": {
            "exchange_code": "US",
        },
    })
    add_test({
        "name": "Exchange details: US (explicit window)",
        "tool": "get_exchange_details",
        "use_common": ["fmt", "api_token"],
        "params": {
            "exchange_code": "US",
            "start_date": "2023-04-01",
            "end_date": "2024-02-28",
        },
    })

    # --- Macro Indicators ---
    add_test({
        "name": "Macro: USA default (gdp_current_usd)",
        "tool": "get_macro_indicator",
        "use_common": ["fmt", "api_token"],
        "params": {
            "country": "USA",
        },
    })
    add_test({
        "name": "Macro: FRA inflation_consumer_prices_annual",
        "tool": "get_macro_indicator",
        "use_common": ["fmt", "api_token"],
        "params": {
            "country": "FRA",
            "indicator": "inflation_consumer_prices_annual",
        },
    })

    # --- User details ---
    add_test({
        "name": "User details (env or override token)",
        "tool": "get_user_details",
        "use_common": ["api_token"],  # token taken from env by default
        "params": {
            # "api_token": "YOUR_REAL_API_TOKEN",
        },
    })

    # --- Symbol Change History ---
    add_test({
        "name": "Symbol Change History: Oct–Nov 2022",
        "tool": "get_symbol_change_history",
        "use_common": ["fmt", "api_token"],
        "params": {
            "start_date": "2022-10-01",
            "end_date": "2022-11-01",
        },
    })

    # --- Historical Market Cap ---
    add_test({
        "name": "Historical Market Cap: AAPL weekly (demo window)",
        "tool": "get_historical_market_cap",
        "use_common": ["fmt", "api_token"],
        "params": {
            "ticker": "AAPL.US",
            "start_date": "2025-03-01",
            "end_date": "2025-04-01",
        },
    })

    # --- Insider Transactions ---
    add_test({
        "name": "Insider Transactions: general window",
        "tool": "get_insider_transactions",
        "use_common": ["fmt", "api_token"],
        "params": {
            "start_date": "2024-03-01",
            "end_date": "2024-03-02",
            "limit": 20,
        },
    })
    add_test({
        "name": "Insider Transactions: AAPL filter",
        "tool": "get_insider_transactions",
        "use_common": ["fmt", "api_token", "symbol"],
        "params": {
            "start_date": "2024-03-01",
            "end_date": "2024-03-15",
            "limit": 10,
        },
    })

    # --- WebSockets: US trades (AAPL, MSFT, TSLA) ---
    add_test({
        "name": "WS: US trades AAPL,MSFT,TSLA (demo)",
        "tool": "capture_realtime_ws",
        "use_common": ["api_token"],
        "params": {
            "feed": "us_trades",
            "symbols": ["AAPL", "MSFT", "TSLA"],  # demo supports these
            "duration_seconds": 4,
            # "max_messages": 200,  # optional safety cap
        },
    })

    # --- WebSockets: Crypto (ETH-USD, BTC-USD) ---
    add_test({
        "name": "WS: Crypto ETH-USD,BTC-USD (demo)",
        "tool": "capture_realtime_ws",
        "use_common": ["api_token"],
        "params": {
            "feed": "crypto",
            "symbols": ["ETH-USD", "BTC-USD"],
            "duration_seconds": 4,
        },
    })

    # --- WebSockets: Forex (EURUSD) ---
    add_test({
        "name": "WS: Forex EURUSD (demo)",
        "tool": "capture_realtime_ws",
        "use_common": ["api_token"],
        "params": {
            "feed": "forex",
            "symbols": "EURUSD",
            "duration_seconds": 4,
        },
    })

    # --- US Tick Data: AAPL sample window (docs example times) ---
    add_test({
        "name": "US Ticks: AAPL 2023-09-11 18:00 → 2023-09-12 18:00 (limit 5)",
        "tool": "get_us_tick_data",
        "use_common": ["fmt", "api_token", "ticker"],  # token via env or override in params
        "params": {
            "from_timestamp": 1694455200,  # 2023-09-11 18:00:00 UTC
            "to_timestamp": 1694541600,  # 2023-09-12 18:00:00 UTC
            "limit": 5,
        },
    })

    # Optional: another quick tick sample (TSLA) if you have a paid token
    add_test({
        "name": "US Ticks: TSLA short window (limit 5)",
        "tool": "get_us_tick_data",
        "use_common": ["fmt", "api_token"],
        "params": {
            "ticker": "TSLA",
            "from_timestamp": 1694455200,
            "to_timestamp": 1694462400,  # +2h
            "limit": 5,
            # "api_token": "YOUR_TOKEN",
        },
    })

    # 1) OPTIONS: Get contracts — narrow filter, fields subset, limit 5
    add_test({
        "name": "Options: contracts (AAPL, strike=450 put, exp=2027-01-15, fields subset, limit=5)",
        "tool": "get_us_options_contracts",
        "use_common": ["api_token", "fmt"],
        "params": {
            "underlying_symbol": "AAPL",
            "strike_eq": 450,
            "type": "put",
            "exp_date_eq": "2027-01-15",
            "fields": ["contract", "bid_date", "open", "high", "low", "last"],
            "page_limit": 5,
            "sort": "-exp_date",
            # "api_token": "demo",  # demo works for AAPL
        },
    })

    # Broader contracts query to exercise pagination/meta/links
    add_test({
        "name": "Options: contracts (AAPL, limit=4)",
        "tool": "get_us_options_contracts",
        "use_common": ["api_token", "fmt"],
        "params": {
            "underlying_symbol": "AAPL",
            "page_limit": 4,
            # "api_token": "demo",
        },
    })

    # 2) OPTIONS EOD: by contract with field subset, limit=5, compact off
    add_test({
        "name": "Options: EOD (AAPL270115P00450000, fields subset, limit=5, compact=0)",
        "tool": "get_us_options_eod",
        "use_common": ["api_token", "fmt"],
        "params": {
            "contract": "AAPL270115P00450000",
            "strike_eq": 450,
            "type": "put",
            "exp_date_eq": "2027-01-15",
            "fields": ["contract", "bid_date", "open", "high", "low", "last"],
            "page_limit": 5,
            "sort": "-exp_date",
            "compact": False,
            # "api_token": "demo",
        },
    })

    # OPTIONS EOD: minimal filter by contract only, default fields, limit=5
    add_test({
        "name": "Options: EOD (contract only, limit=5)",
        "tool": "get_us_options_eod",
        "use_common": ["api_token", "fmt"],
        "params": {
            "contract": "AAPL270115P00450000",
            "page_limit": 5,
            # "api_token": "demo",
        },
    })

    # 3) OPTIONS: underlying symbols list
    add_test({
        "name": "Options: underlying symbols list",
        "tool": "get_us_options_underlyings",
        "use_common": ["api_token", "fmt"],
        "params": {
            # You can add page_offset/page_limit if you want smaller page sizes:
            "page_limit": 50,
            # "api_token": "demo",
        },
    })

    # Economic Events: US, 2025-01-05 to 2025-01-06 (docs-like example), large limit
    add_test({
        "name": "Economic Events: US window (2025-01-05..2025-01-06, limit=1000)",
        "tool": "get_economic_events",
        "use_common": ["fmt", "api_token"],  # use COMMON defaults for fmt/json if you defined them
        "params": {
            "start_date": "2025-01-05",
            "end_date": "2025-01-06",
            "country": "US",
            "limit": 1000,
            # "api_token": "YOUR_TOKEN",  # or rely on env EODHD_API_KEY
        },
    })

    # Economic Events: filter by comparison + type (illustrative)
    add_test({
        "name": "Economic Events: comparison=mom + type='Factory Orders'",
        "tool": "get_economic_events",
        "use_common": ["fmt", "api_token"],
        "params": {
            "start_date": "2025-01-05",
            "end_date": "2025-01-06",
            "country": "US",
            "comparison": "mom",
            "type": "Factory Orders",
            "limit": 200,
        },
    })

    # Earnings by date window (docs-style example)
    add_test({
        "name": "Upcoming Earnings: window 2018-12-02..2018-12-03 (json)",
        "tool": "get_upcoming_earnings",
        "use_common": ["fmt", "api_token"],  # will default to json if COMMON sets it
        "params": {
            "start_date": "2018-12-02",
            "end_date": "2018-12-03",
            # "fmt": "json",
            # "api_token": "YOUR_TOKEN",  # or rely on env EODHD_API_KEY
        },
    })

    # Earnings for specific symbols (AAPL.US, MSFT.US, AI.PA) — from/to ignored by API when symbols present
    add_test({
        "name": "Upcoming Earnings: symbols AAPL.US,MSFT.US,AI.PA (json)",
        "tool": "get_upcoming_earnings",
        "use_common": ["fmt", "api_token"],
        "params": {
            "symbols": ["AAPL.US", "MSFT.US", "AI.PA"],
            "start_date": "2018-01-01",  # will be ignored by API when symbols present
            "end_date": "2018-04-04",  # will be ignored by API when symbols present
            # "fmt": "json",
        },
    })
    # --- Earnings Trends: single symbol (AAPL.US) ---
    add_test({
        "name": "Earnings Trends: AAPL.US",
        "tool": "get_earnings_trends",
        "use_common": ["fmt", "api_token"],  # COMMON["fmt"] typically "json"
        "params": {
            "symbols": "AAPL.US",
            # "fmt": "json",
            # "api_token": "YOUR_TOKEN",  # optional; default env EODHD_API_KEY
        },
    })

    # --- Earnings Trends: multiple symbols (AAPL.US, MSFT.US, AI.PA) ---
    add_test({
        "name": "Earnings Trends: AAPL.US,MSFT.US,AI.PA",
        "tool": "get_earnings_trends",
        "use_common": ["fmt", "api_token"],
        "params": {
            "symbols": ["AAPL.US", "MSFT.US", "AI.PA"],
            # "fmt": "json",
        },
    })
    # --- Upcoming IPOs: windowed, JSON ---
    add_test({
        "name": "Upcoming IPOs: 2018-12-02..2018-12-06 (JSON)",
        "tool": "get_upcoming_ipos",
        "use_common": ["api_token", "fmt"],
        "params": {
            "from_date": "2018-12-02",
            "to_date": "2018-12-06",
            # "api_token": "YOUR_TOKEN",  # optional, else env EODHD_API_KEY
        },
    })

    # --- Upcoming IPOs: default server window (today..+7) ---
    add_test({
        "name": "Upcoming IPOs: default window (server)",
        "tool": "get_upcoming_ipos",
        "use_common": ["fmt", "api_token"],
        "params": {
            # "fmt": "json",
        },
    })

    # --- Upcoming IPOs: CSV sample (optional) ---
    add_test({
        "name": "Upcoming IPOs: CSV sample window",
        "tool": "get_upcoming_ipos",
        "use_common": ["api_token"],
        "params": {
            "from_date": "2018-12-02",
            "to_date": "2018-12-06",
            "fmt": "csv",
        },
    })

    # --- Upcoming Splits: explicit window, JSON ---
    add_test({
        "name": "Upcoming Splits: 2018-12-02..2018-12-06 (JSON)",
        "tool": "get_upcoming_splits",
        "use_common": ["fmt", "api_token"],
        "params": {
            "from_date": "2018-12-02",
            "to_date": "2018-12-06",
            # "fmt": "json",
            # "api_token": "YOUR_TOKEN",  # optional; else env EODHD_API_KEY
        },
    })



    # --- Upcoming Splits: server default window (today..+7) ---
    add_test({
        "name": "Upcoming Splits: default window (server)",
        "tool": "get_upcoming_splits",
        "use_common": ["fmt", "api_token"],
        "params": {
            # "fmt": "json",
        },
    })

    # --- Upcoming Splits: CSV sample ---
    add_test({
        "name": "Upcoming Splits: CSV (2018-12-02..2018-12-06)",
        "tool": "get_upcoming_splits",
        "use_common": ["api_token"],
        "params": {
            "from_date": "2018-12-02",
            "to_date": "2018-12-06",
            "fmt": "csv",
        },
    })

    # --- Dividends: by symbol only (default pagination) ---
    add_test({
        "name": "Dividends: by symbol (AAPL.US)",
        "tool": "get_upcoming_dividends",
        "use_common": ["fmt", "api_token"],
        "params": {
            "symbol": "AAPL.US",
            # fmt is provided via use_common
        },
    })

    # --- Dividends: exact date only (no symbol) ---
    add_test({
        "name": "Dividends: by exact date only",
        "tool": "get_upcoming_dividends",
        "use_common": ["fmt", "api_token"],
        "params": {
            "date_eq": "2024-11-08",  # example Apple dividend date from docs
        },
    })

    # --- Dividends: date window + symbol + pagination ---
    add_test({
        "name": "Dividends: by symbol and date range with pagination",
        "tool": "get_upcoming_dividends",
        "use_common": ["fmt", "api_token"],
        "params": {
            "symbol": "AAPL.US",
            "date_from": "2023-01-01",
            "date_to": "2023-12-31",
            "page_limit": 100,
            "page_offset": 0,
        },
    })

    # --- mp_indices_list: happy path JSON ---
    add_test({
        "name": "MP Indices List: JSON basics",
        "tool": "mp_indices_list",
        "use_common": ["fmt", "api_token"],  # if COMMON has fmt='json'
        "params": {
            # "fmt": "json",
            # "api_token": "YOUR_TOKEN",  # optional; else env EODHD_API_KEY
        },
    })

    # --- mp_index_components: S&P 500 (sample) ---
    add_test({
        "name": "MP Index Components: GSPC.INDX JSON",
        "tool": "mp_index_components",
        "use_common": ["fmt", "api_token"],  # if COMMON has fmt='json'
        "params": {
            "symbol": "GSPC.INDX",
            # "fmt": "json",
        },
    })

    # --- Stock Screener: happy path with JSON filters (as string) ---
    add_test({
        "name": "Screener: basic market_cap desc with filter string",
        "tool": "stock_screener",
        "use_common": ["fmt", "api_token"],
        "params": {
            "sort": "market_capitalization.desc",
            "filters": '[[\"market_capitalization\",\"\\u003e\",1000],[\"name\",\"match\",\"apple\"],[\"code\",\"=\",\"AAPL\"],[\"exchange\",\"=\",\"us\"],[\"sector\",\"=\",\"Technology\"]]',
            "limit": 10,
            "offset": 0
        },
    })

    # --- Stock Screener: python list filters (module will JSON-encode) ---
    add_test({
        "name": "Screener: list filters + signals list",
        "tool": "stock_screener",
        "use_common": ["fmt", "api_token"],
        "params": {
            "sort": "market_capitalization.desc",
            "filters": [
                ["market_capitalization", ">", 10000]
            ],
            "signals": ["bookvalue_neg", "200d_new_lo"],
            "limit": 10,
            "offset": 0
        },
    })

    # --- Stock Screener: signals as comma string ---
    add_test({
        "name": "Screener: signals string",
        "tool": "stock_screener",
        "use_common": ["fmt", "api_token"],
        "params": {
            "signals": "bookvalue_neg,200d_new_lo",
            "limit": 5,
            "offset": 0
        },
    })

    # --- Fundamentals: Common Stock (no date pruning, full sections + financials maps) ---
    add_test({
        "name": "Fundamentals: stock full",
        "tool": "get_fundamentals_data",
        "use_common": ["api_token"],
        "params": {
            "ticker": "AAPL.US",
            # no from/to -> module fetches full Financials::{stmt}::{quarterly,yearly} maps
            "include_financials": True,
        },
    })

    # --- Fundamentals: Common Stock with from/to pruning (fetch only in-range leaves) ---
    add_test({
        "name": "Fundamentals: stock pruned window",
        "tool": "get_fundamentals_data",
        "use_common": ["api_token"],
        "params": {
            "ticker": "AAPL.US",
            "from_date": "2023-01-01",
            "to_date": "2024-12-31",
            "include_financials": True,
        },
    })

    # --- Fundamentals: ETF basic (General, Technicals, ETF_Data) ---
    add_test({
        "name": "Fundamentals: ETF basic",
        "tool": "get_fundamentals_data",
        "use_common": ["api_token"],
        "params": {
            "ticker": "VTI.US",
            # sections omitted -> module defaults to General, Technicals, ETF_Data
        },
    })

    # --- Fundamentals: Mutual Fund basic (General, MutualFund_Data) ---
    add_test({
        "name": "Fundamentals: Fund basic",
        "tool": "get_fundamentals_data",
        "use_common": ["api_token"],
        "params": {
            "ticker": "SWPPX.US",
            # sections omitted -> module defaults to General, MutualFund_Data
        },
    })

    # --- Fundamentals: Index with historical snapshots and bounded window (pass-through extra_params) ---
    add_test({
        "name": "Fundamentals: Index historical window",
        "tool": "get_fundamentals_data",
        "use_common": ["api_token"],
        "params": {
            "ticker": "GSPC.INDX",
            "extra_params": {
                "historical": 1,
                "from": "2020-01-01",
                "to": "2023-01-01",
            },
            # sections omitted -> defaults to General (HistoricalComponents controlled by extra_params on server)
        },
    })

    # --- Fundamentals: BTC-USD.CC (General, Tech, Resources, Statistics) ---
    add_test({
        "name": "Fundamentals: Cryptocurrency",
        "tool": "get_fundamentals_data",
        "use_common": ["api_token"],
        "params": {
            "ticker": "BTC-USD.CC",
            # sections omitted -> module defaults to General, Tech, Resources, Statistics
        },
    })

    # --- Fundamentals: EURUSD.FOREX (General only) ---
    add_test({
        "name": "Fundamentals: Currency",
        "tool": "get_fundamentals_data",
        "use_common": ["api_token"],
        "params": {
            "ticker": "EURUSD.FOREX",
            # sections omitted -> module defaults to General
        },
    })

    # tests/catalog_technical_indicators.py

    # --- SMA ---
    add_test({
        "name": "technical: SMA 30 AAPL.US",
        "tool": "get_technical_indicators",
        "use_common": ["fmt", "api_token"],
        "params": {
            "ticker": "AAPL.US",
            "function": "sma",
            "start_date": "2022-08-10",
            "end_date": "2022-10-01",
            "order": "d",
            "period": 30,
        },
    })

    # --- EMA (filter last) ---
    add_test({
        "name": "technical: EMA last_ema AAPL.US",
        "tool": "get_technical_indicators",
        "use_common": ["fmt", "api_token"],
        "params": {
            "ticker": "AAPL.US",
            "function": "ema",
            "filter": "last_ema",
            "order": "d",
            "period": 50,
        },
    })

    # --- MACD with custom periods ---
    add_test({
        "name": "technical: MACD custom AAPL.US",
        "tool": "get_technical_indicators",
        "use_common": ["fmt", "api_token"],
        "params": {
            "ticker": "AAPL.US",
            "function": "macd",
            "start_date": "2022-08-05",
            "end_date": "2022-10-01",
            "order": "d",
            "fast_period": 13,
            "slow_period": 26,
            "signal_period": 12,
        },
    })

    # --- Stochastic ---
    add_test({
        "name": "technical: Stochastic K/D AAPL.US",
        "tool": "get_technical_indicators",
        "use_common": ["fmt", "api_token"],
        "params": {
            "ticker": "AAPL.US",
            "function": "stochastic",
            "start_date": "2022-06-01",
            "end_date": "2022-10-01",
            "order": "d",
            "fast_kperiod": 14,
            "slow_kperiod": 5,
            "slow_dperiod": 4,
        },
    })

    # --- StochRSI ---
    add_test({
        "name": "technical: StochRSI AAPL.US",
        "tool": "get_technical_indicators",
        "use_common": ["fmt", "api_token"],
        "params": {
            "ticker": "AAPL.US",
            "function": "stochrsi",
            "start_date": "2022-06-05",
            "end_date": "2022-10-01",
            "order": "d",
            "fast_kperiod": 14,
            "fast_dperiod": 14,
        },
    })

    # --- ATR ---
    add_test({
        "name": "technical: ATR 50 AAPL.US",
        "tool": "get_technical_indicators",
        "use_common": ["fmt", "api_token"],
        "params": {
            "ticker": "AAPL.US",
            "function": "atr",
            "start_date": "2022-07-15",
            "end_date": "2022-10-01",
            "order": "d",
            "period": 50,
        },
    })

    # --- SAR (acceleration/maximum) ---
    add_test({
        "name": "technical: SAR custom AAPL.US",
        "tool": "get_technical_indicators",
        "use_common": ["fmt", "api_token"],
        "params": {
            "ticker": "AAPL.US",
            "function": "sar",
            "start_date": "2022-09-25",
            "end_date": "2022-10-01",
            "order": "d",
            "acceleration": 0.03,
            "maximum": 0.21,
        },
    })

    # --- Beta vs NDX.INDX ---
    add_test({
        "name": "technical: BETA vs NDX.INDX AAPL.US",
        "tool": "get_technical_indicators",
        "use_common": ["fmt", "api_token"],
        "params": {
            "ticker": "AAPL.US",
            "function": "beta",
            "start_date": "2022-07-15",
            "end_date": "2022-10-01",
            "order": "d",
            "period": 50,
            "code2": "NDX.INDX",
        },
    })

    # --- Bollinger Bands ---
    add_test({
        "name": "technical: BBANDS 50 AAPL.US",
        "tool": "get_technical_indicators",
        "use_common": ["fmt", "api_token"],
        "params": {
            "ticker": "AAPL.US",
            "function": "bbands",
            "start_date": "2022-07-15",
            "end_date": "2022-10-01",
            "order": "d",
            "period": 50,
        },
    })

    # --- Split Adjusted (agg_period) ---
    add_test({
        "name": "technical: splitadjusted daily AAPL.US",
        "tool": "get_technical_indicators",
        "use_common": ["fmt", "api_token"],
        "params": {
            "ticker": "AAPL.US",
            "function": "splitadjusted",
            "start_date": "2022-09-20",
            "end_date": "2022-10-01",
            "order": "d",
            "agg_period": "d",
        },
    })

    # --- AmiBroker format ---
    add_test({
        "name": "technical: format_amibroker AAPL.US",
        "tool": "get_technical_indicators",
        "use_common": ["fmt", "api_token"],
        "params": {
            "ticker": "AAPL.US",
            "function": "format_amibroker",
            "start_date": "2022-09-25",
            "end_date": "2022-10-01",
            "order": "d",
        },
    })

    # --- Live v2: single symbol ---
    add_test({
        "name": "Live v2: AAPL.US extended quote",
        "tool": "get_us_live_extended_quotes",
        "use_common": ["fmt", "api_token"],
        "params": {
            "symbols": ["AAPL.US"],
        },
    })

    # --- Live v2: batch with pagination params ---
    add_test({
        "name": "Live v2: Batch AAPL/TSLA/JPM (limit=100, offset=0)",
        "tool": "get_us_live_extended_quotes",
        "use_common": ["fmt", "api_token"],
        "params": {
            "symbols": ["AAPL.US", "TSLA.US", "JPM.US"],
            "page_limit": 100,
            "page_offset": 0,
        },
    })

    # --- Live v2: CSV output (if your make_request supports raw text passthrough) ---
    add_test({
        "name": "Live v2: AAPL.US extended quote CSV",
        "tool": "get_us_live_extended_quotes",
        "use_common": ["api_token"],  # fmt overridden below
        "params": {
            "symbols": ["AAPL.US"],
            "fmt": "csv",
        },
    })

    # --- CBOE Indices List ---

    # Basic happy-path call using common fmt/api_token
    add_test({
        "name": "CBOE indices: list (basic)",
        "tool": "get_cboe_indices_list",
        "use_common": ["fmt", "api_token"],
        "params": {
            # no extra params; uses defaults + COMMON
        },
    })

    # --- CBOE Index Feed API ---

    # Happy path: full filter set for BDE30P
    add_test({
        "name": "CBOE index feed: BDE30P 2017-02-01 snapshot_official_closing",
        "tool": "get_cboe_index_data",
        "use_common": ["fmt", "api_token"],
        "params": {
            "index_code": "BDE30P",
            "feed_type": "snapshot_official_closing",
            "date": "2017-02-01",
        },
    })


    # --- illio: S&P 500 ---
    add_test({
        "name": "illio: Performance Insights SnP500",
        "tool": "mp_illio_performance_insights",
        "use_common": ["fmt", "api_token"],
        "params": {
            "id": "SnP500",
        },
    })

    # --- illio: Dow 30 (accept alias) ---
    add_test({
        "name": "illio: Performance Insights DJI (alias: dow)",
        "tool": "mp_illio_performance_insights",
        "use_common": ["fmt", "api_token"],
        "params": {
            "id": "dow",  # alias -> DJI
        },
    })

    # --- illio: Nasdaq-100 (accept alias) ---
    add_test({
        "name": "illio: Performance Insights NDX (alias: nasdaq100)",
        "tool": "mp_illio_performance_insights",
        "use_common": ["fmt", "api_token"],
        "params": {
            "id": "nasdaq100",  # alias -> NDX
        },
    })

    # --- illio: S&P 500 ---
    add_test({
        "name": "illio: Risk Insights SnP500",
        "tool": "mp_illio_risk_insights",
        "use_common": ["fmt", "api_token"],
        "params": {
            "id": "SnP500",
        },
    })

    # --- illio: Dow 30 (accept alias) ---
    add_test({
        "name": "illio: Risk Insights DJI (alias: dow)",
        "tool": "mp_illio_risk_insights",
        "use_common": ["fmt", "api_token"],
        "params": {
            "id": "dow",  # alias -> DJI
        },
    })

    # --- illio: Nasdaq-100 (accept alias) ---
    add_test({
        "name": "illio: Risk Insights NDX (alias: nasdaq100)",
        "tool": "mp_illio_risk_insights",
        "use_common": ["fmt", "api_token"],
        "params": {
            "id": "nasdaq100",  # alias -> NDX
        },
    })

    # --- illio: market insights SnP500---
    add_test({
        "name": "illio: Market Insights SnP500",
        "tool": "get_mp_illio_market_insights_performance",
        "use_common": ["fmt", "api_token"],
        "params": {"id": "SnP500"},
    })

    # --- illio: market insights DJI---
    add_test({
        "name": "illio: Market Insights DJI (alias: dow)",
        "tool": "get_mp_illio_market_insights_performance",
        "use_common": ["fmt", "api_token"],
        "params": {"id": "dow"},  # alias -> DJI
    })

    # --- illio: market insights NDX---
    add_test({
        "name": "illio: Market Insights NDX (alias: nasdaq100)",
        "tool": "get_mp_illio_market_insights_performance",
        "use_common": ["fmt", "api_token"],
        "params": {"id": "nasdaq100"},  # alias -> NDX
    })

    # --- illio: Best/Worst SnP500 ---
    add_test({
        "name": "illio: Best/Worst SnP500",
        "tool": "get_mp_illio_market_insights_best_worst",
        "use_common": ["fmt", "api_token"],
        "params": {"id": "SnP500"},
    })

    # --- illio: Best/Worst Dow 30 (accept alias) ---
    add_test({
        "name": "illio: Best/Worst DJI (alias: dow)",
        "tool": "get_mp_illio_market_insights_best_worst",
        "use_common": ["fmt", "api_token"],
        "params": {"id": "dow"},  # alias -> DJI
    })

    # --- illio: Best/Worst Nasdaq-100 (accept alias) ---
    add_test({
        "name": "illio: Best/Worst NDX (alias: nasdaq100)",
        "tool": "get_mp_illio_market_insights_best_worst",
        "use_common": ["fmt", "api_token"],
        "params": {"id": "nasdaq100"},  # alias -> NDX
    })

    # --- alias tool still works ---
    add_test({
        "name": "illio(alias): Best/Worst SnP500",
        "tool": "mp_illio_market_insights_best_worst",
        "use_common": ["fmt", "api_token"],
        "params": {"id": "SnP500"},
    })

    # --- illio: Volatility Bands vs Market (Nasdaq 100 via alias) ---
    add_test({
        "name": "illio: Volatility Bands NDX",
        "tool": "mp_illio_market_insights_volatility",
        "use_common": ["fmt", "api_token"],
        "params": {
            "id": "NDX",
        },
    })

    # --- illio: Volatility Bands vs Market (SnP500 via alias) ---
    add_test({
        "name": "illio: Volatility Bands SnP500 (alias: spx)",
        "tool": "mp_illio_market_insights_volatility",
        "use_common": ["fmt", "api_token"],
        "params": {
            "id": "spx",  # alias -> SnP500
        },
    })

    # --- illio: Risk-Return SnP500 ---
    add_test({
        "name": "illio: Market Insights Risk-Return SnP500",
        "tool": "get_mp_illio_market_insights_risk_return",
        "use_common": ["fmt", "api_token"],
        "params": {
            "id": "SnP500",
        },
    })

    # --- illio: Risk-Return Nasdaq-100 (alias) ---
    add_test({
        "name": "illio: Market Insights Risk-Return NDX (alias: nasdaq100)",
        "tool": "get_mp_illio_market_insights_risk_return",
        "use_common": ["fmt", "api_token"],
        "params": {
            "id": "nasdaq100",  # alias -> NDX
        },
    })

    # --- illio: Largest Volatility Change SnP500 ---
    add_test({
        "name": "illio: Market Insights Largest Volatility Change SnP500",
        "tool": "get_mp_illio_market_insights_largest_volatility",
        "use_common": ["fmt", "api_token"],
        "params": {
            "id": "SnP500",
        },
    })

    # --- illio: Largest Volatility Change Nasdaq-100 (alias) ---
    add_test({
        "name": "illio: Market Insights Largest Volatility Change NDX (alias: nasdaq100)",
        "tool": "get_mp_illio_market_insights_largest_volatility",
        "use_common": ["fmt", "api_token"],
        "params": {
            "id": "nasdaq100",  # alias -> NDX
        },
    })

    # --- illio Market Insights: Beta Bands Insight (primary tool) ---
    add_test({
        "name": "illio Market Insights: Beta Bands (NDX)",
        "tool": "get_mp_illio_market_insights_beta_bands",
        "use_common": ["api_token"],
        "params": {
            "id": "NDX",
        },
    })

    # --- illio Market Insights: Beta Bands – alias tool ---
    add_test({
        "name": "illio Market Insights: Beta Bands via alias tool (SnP500 alias)",
        "tool": "get_mp_illio_market_insights_beta_bands",
        "use_common": ["api_token"],
        "params": {
            "id": "SP500",   # should normalize to canonical 'SnP500'
        },
    })

    # --- Praams Risk Scoring by Ticker ---
    add_test({
        "name": "Praams Risk Scoring by Ticker (AAPL)",
        "tool": "get_mp_praams_risk_scoring_by_ticker",
        "use_common": ["api_token"],
        "params": {
            "ticker": "AAPL",
        },
    })

    # --- Praams Risk Scoring by ISIN ---
    add_test({
        "name": "Praams Risk Scoring by ISIN (US88160R1014)",
        "tool": "get_mp_praams_risk_scoring_by_isin",
        "use_common": ["api_token"],
        "params": {
            "isin": "US88160R1014",
        },
    })

    # --- Praams Bond Analyze by ISIN ---
    add_test({
        "name": "Praams Bond Analyze by ISIN (US7593518852)",
        "tool": "get_mp_praams_bond_analyze_by_isin",
        "use_common": ["api_token"],
        "params": {
            "isin": "US7593518852",
        },
    })

    # --- Praams Bank Income Statement by Ticker ---
    add_test({
        "name": "Praams Bank Income Statement retrieval by Ticker (JPM)",
        "tool": "get_mp_praams_bank_income_statement_by_ticker",
        "use_common": ["api_token"],
        "params": {
            "ticker": "JPM",
        },
    })

    # --- Praams Bank Income Statement by ISIN ---
    add_test({
        "name": "Praams Bank Income Statement retrieval by ISIN (US46625H1005)",
        "tool": "get_mp_praams_bank_income_statement_by_isin",
        "use_common": ["api_token"],
        "params": {
            "isin": "US46625H1005",
        },
    })

    # --- Praams Bank Balance Sheet by Ticker ---
    add_test({
        "name": "Praams Bank Balance Sheet retrieval by Ticker (JPM)",
        "tool": "get_mp_praams_bank_balance_sheet_by_ticker",
        "use_common": ["api_token"],
        "params": {
            "ticker": "JPM",
        },
    })

    # --- Praams Bank Income Statement by ISIN ---
    add_test({
        "name": "Praams Bank Balance Sheet retrieval by ISIN (US46625H1005)",
        "tool": "get_mp_praams_bank_balance_sheet_by_isin",
        "use_common": ["api_token"],
        "params": {
            "isin": "US46625H1005",
        },
    })

    # --- Investverte ESG: List Companies ---

    # Basic happy-path call using common fmt/api_token
    add_test({
        "name": "Investverte: ESG list companies (basic)",
        "tool": "get_mp_investverte_esg_list_companies",
        "use_common": ["fmt", "api_token"],
        "params": {
            # no extra params; uses defaults + COMMON
        },
    })

    # --- Investverte ESG: List Countries ---

    # Basic happy-path call using common fmt/api_token
    add_test({
        "name": "Investverte: ESG list countries (basic)",
        "tool": "get_mp_investverte_esg_list_countries",
        "use_common": ["fmt", "api_token"],
        "params": {
            # no extra params; uses defaults + COMMON
        },
    })

    # --- Investverte ESG: View Country ---

    # Basic: all years/frequencies for US
    add_test({
        "name": "Investverte: View country US (all years)",
        "tool": "get_mp_investverte_esg_view_country",
        "use_common": ["fmt", "api_token"],
        "params": {
            "symbol": "US",
        },
    })

    # Specific year + frequency
    add_test({
        "name": "Investverte: View country US 2021 FY",
        "tool": "get_mp_investverte_esg_view_country",
        "use_common": ["fmt", "api_token"],
        "params": {
            "symbol": "US",
            "year": 2021,
            "frequency": "FY",
        },
    })

    # --- Investverte ESG: View Company ---

    # Specific year + frequency for a well-known symbol
    add_test({
        "name": "Investverte: View company AAPL 2021 FY",
        "tool": "get_mp_investverte_esg_view_company",
        "use_common": ["fmt", "api_token"],
        "params": {
            "symbol": "AAPL",
            "year": 2021,
            "frequency": "FY",
        },
    })

    # All years/frequencies for a symbol
    add_test({
        "name": "Investverte: View company 000039.SZ (all years)",
        "tool": "get_mp_investverte_esg_view_company",
        "use_common": ["fmt", "api_token"],
        "params": {
            "symbol": "000039.SZ",
        },
    })

    # --- Investverte ESG: List Sectors ---

    # Basic happy-path call using common fmt/api_token
    add_test({
        "name": "Investverte: ESG list sectors (basic)",
        "tool": "get_mp_investverte_esg_list_sectors",
        "use_common": ["fmt", "api_token"],
        "params": {
            # no extra params; uses defaults + COMMON
        },
    })

    # --- Investverte ESG: View Sector ---

    # Basic: sector "Airlines"
    add_test({
        "name": "Investverte: View sector Airlines (basic)",
        "tool": "get_mp_investverte_esg_view_sector",
        "use_common": ["fmt", "api_token"],
        "params": {
            "symbol": "Airlines",
        },
    })

    # ============================================================
    # v2.6.0 New Tools Integration Tests
    # ============================================================

    # --- ESG Scores ---
    add_test({
        "name": "ESG Scores: AAPL.US",
        "tool": "get_esg_scores",
        "use_common": ["api_token"],
        "params": {
            "ticker": "AAPL.US",
        },
    })

    # --- Analyst Ratings ---
    add_test({
        "name": "Analyst Ratings: AAPL.US",
        "tool": "get_analyst_ratings",
        "use_common": ["api_token"],
        "params": {
            "ticker": "AAPL.US",
        },
    })

    # --- Price Targets ---
    add_test({
        "name": "Price Targets: MSFT.US",
        "tool": "get_price_targets",
        "use_common": ["api_token"],
        "params": {
            "ticker": "MSFT.US",
        },
    })

    # --- Short Interest ---
    add_test({
        "name": "Short Interest: TSLA.US",
        "tool": "get_short_interest",
        "use_common": ["api_token"],
        "params": {
            "ticker": "TSLA.US",
        },
    })

    # --- Institutional Holders ---
    add_test({
        "name": "Institutional Holders: AAPL.US",
        "tool": "get_institutional_holders",
        "use_common": ["api_token"],
        "params": {
            "ticker": "AAPL.US",
        },
    })

    # --- Fund Holdings ---
    add_test({
        "name": "Fund Holdings: VTI.US",
        "tool": "get_fund_holdings",
        "use_common": ["api_token"],
        "params": {
            "ticker": "VTI.US",
        },
    })

    # --- Bulk EOD Data ---
    add_test({
        "name": "Bulk EOD: US exchange",
        "tool": "get_bulk_eod",
        "use_common": ["api_token"],
        "params": {
            "exchange": "US",
            "date": "2024-01-15",
        },
    })

    # --- Bonds Fundamentals ---
    add_test({
        "name": "Bonds Fundamentals: US0378331005",
        "tool": "get_bond_fundamentals",
        "use_common": ["api_token"],
        "params": {
            "isin": "US0378331005",
        },
    })

    # --- Exchange Symbols ---
    add_test({
        "name": "Exchange Symbols: US",
        "tool": "get_exchange_symbols",
        "use_common": ["api_token", "fmt"],
        "params": {
            "exchange": "US",
        },
    })

    # --- Trading Hours ---
    add_test({
        "name": "Trading Hours: US",
        "tool": "get_trading_hours",
        "use_common": ["api_token"],
        "params": {
            "exchange": "US",
        },
    })

    # --- Available Exchanges ---
    add_test({
        "name": "Available Exchanges List",
        "tool": "get_available_exchanges",
        "use_common": ["api_token", "fmt"],
        "params": {},
    })

    # --- Financial News ---
    add_test({
        "name": "Financial News: general",
        "tool": "get_financial_news",
        "use_common": ["api_token"],
        "params": {
            "limit": 10,
        },
    })

    add_test({
        "name": "Financial News: by ticker AAPL",
        "tool": "get_financial_news",
        "use_common": ["api_token"],
        "params": {
            "ticker": "AAPL.US",
            "limit": 5,
        },
    })

    # --- Outgoing Earnings ---
    add_test({
        "name": "Outgoing Earnings: AAPL.US",
        "tool": "get_outgoing_earnings",
        "use_common": ["api_token"],
        "params": {
            "ticker": "AAPL.US",
        },
    })

    # --- Splits History ---
    add_test({
        "name": "Splits History: AAPL.US",
        "tool": "get_splits_history",
        "use_common": ["api_token"],
        "params": {
            "ticker": "AAPL.US",
        },
    })

    # --- Dividends History ---
    add_test({
        "name": "Dividends History: AAPL.US",
        "tool": "get_dividends_history",
        "use_common": ["api_token"],
        "params": {
            "ticker": "AAPL.US",
        },
    })

    # --- Batch Quotes ---
    add_test({
        "name": "Batch Quotes: AAPL, MSFT, GOOGL",
        "tool": "get_batch_quotes",
        "use_common": ["api_token"],
        "params": {
            "tickers": ["AAPL.US", "MSFT.US", "GOOGL.US"],
        },
    })

    # --- Historical Dividends ---
    add_test({
        "name": "Historical Dividends: AAPL.US 2023",
        "tool": "get_historical_dividends",
        "use_common": ["api_token"],
        "params": {
            "ticker": "AAPL.US",
            "from_date": "2023-01-01",
            "to_date": "2023-12-31",
        },
    })

    # --- Historical Splits ---
    add_test({
        "name": "Historical Splits: AAPL.US",
        "tool": "get_historical_splits",
        "use_common": ["api_token"],
        "params": {
            "ticker": "AAPL.US",
        },
    })

    # --- Sector Performance ---
    add_test({
        "name": "Sector Performance: US sectors",
        "tool": "get_sector_performance",
        "use_common": ["api_token"],
        "params": {},
    })

    # --- Market Movers ---
    add_test({
        "name": "Market Movers: gainers",
        "tool": "get_market_movers",
        "use_common": ["api_token"],
        "params": {
            "exchange": "US",
            "direction": "gainers",
        },
    })

    add_test({
        "name": "Market Movers: losers",
        "tool": "get_market_movers",
        "use_common": ["api_token"],
        "params": {
            "exchange": "US",
            "direction": "losers",
        },
    })























