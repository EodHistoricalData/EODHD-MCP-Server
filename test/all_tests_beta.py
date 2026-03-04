# This module registers all "new" tests cases to facilitate debugging only new features.

def register(add_test, COMMON):

    # =====================================================================
    #  US Treasury endpoints
    # =====================================================================

    # --- UST Bill Rates: current year default ---
    add_test({
        "name": "UST Bill Rates: current year (default)",
        "tool": "get_ust_bill_rates",
        "use_common": ["api_token"],
        "params": {
            # no year -> defaults to current year
        },
    })

    # --- UST Bill Rates: specific year with pagination ---
    add_test({
        "name": "UST Bill Rates: 2023 (limit=5, offset=0)",
        "tool": "get_ust_bill_rates",
        "use_common": ["api_token"],
        "params": {
            "year": 2023,
            "limit": 5,
            "offset": 0,
        },
    })

    # --- UST Yield Rates: current year default ---
    add_test({
        "name": "UST Yield Rates: current year (default)",
        "tool": "get_ust_yield_rates",
        "use_common": ["api_token"],
        "params": {},
    })

    # --- UST Yield Rates: specific year ---
    add_test({
        "name": "UST Yield Rates: 2023 (limit=5)",
        "tool": "get_ust_yield_rates",
        "use_common": ["api_token"],
        "params": {
            "year": 2023,
            "limit": 5,
        },
    })

    # --- UST Real Yield Rates: current year default ---
    add_test({
        "name": "UST Real Yield Rates: current year (default)",
        "tool": "get_ust_real_yield_rates",
        "use_common": ["api_token"],
        "params": {},
    })

    # --- UST Real Yield Rates: specific year ---
    add_test({
        "name": "UST Real Yield Rates: 2023 (limit=5)",
        "tool": "get_ust_real_yield_rates",
        "use_common": ["api_token"],
        "params": {
            "year": 2023,
            "limit": 5,
        },
    })

    # --- UST Long-Term Rates: current year default ---
    add_test({
        "name": "UST Long-Term Rates: current year (default)",
        "tool": "get_ust_long_term_rates",
        "use_common": ["api_token"],
        "params": {},
    })

    # --- UST Long-Term Rates: specific year ---
    add_test({
        "name": "UST Long-Term Rates: 2023 (limit=5)",
        "tool": "get_ust_long_term_rates",
        "use_common": ["api_token"],
        "params": {
            "year": 2023,
            "limit": 5,
        },
    })

    # =====================================================================
    #  Bulk Fundamentals
    # =====================================================================

    # --- Bulk Fundamentals: US exchange, default pagination ---
    add_test({
        "name": "Bulk Fundamentals: US (default limit/offset)",
        "tool": "get_bulk_fundamentals",
        "use_common": ["api_token"],
        "params": {
            "exchange": "US",
            "limit": 5,
        },
    })

    # --- Bulk Fundamentals: specific symbols ---
    add_test({
        "name": "Bulk Fundamentals: US specific symbols AAPL,MSFT",
        "tool": "get_bulk_fundamentals",
        "use_common": ["api_token"],
        "params": {
            "exchange": "US",
            "symbols": "AAPL,MSFT",
        },
    })

    # =====================================================================
    #  Stock Market Logos
    # =====================================================================

    # --- Stock Market Logos: PNG AAPL.US ---
    add_test({
        "name": "Logo PNG: AAPL.US",
        "tool": "get_stock_market_logos",
        "use_common": ["api_token"],
        "params": {
            "symbol": "AAPL.US",
        },
    })

    # --- Stock Market Logos: SVG AAPL.US ---
    add_test({
        "name": "Logo SVG: AAPL.US",
        "tool": "get_stock_market_logos_svg",
        "use_common": ["api_token"],
        "params": {
            "symbol": "AAPL.US",
        },
    })

    # =====================================================================
    #  Marketplace Tick Data
    # =====================================================================

    # --- MP Tick Data: AAPL sample window ---
    add_test({
        "name": "MP Tick Data: AAPL (limit=5)",
        "tool": "get_mp_tick_data",
        "use_common": ["api_token"],
        "params": {
            "ticker": "AAPL",
            "from_timestamp": 1694455200,  # 2023-09-11 18:00:00 UTC
            "to_timestamp": 1694541600,    # 2023-09-12 18:00:00 UTC
            "limit": 5,
        },
    })

    # =====================================================================
    #  TradingHours Marketplace
    # =====================================================================

    # --- TradingHours: List Markets (core) ---
    add_test({
        "name": "TradingHours: List Markets (core)",
        "tool": "get_mp_tradinghours_list_markets",
        "use_common": ["api_token"],
        "params": {
            "group": "core",
        },
    })

    # --- TradingHours: List Markets (default=all) ---
    add_test({
        "name": "TradingHours: List Markets (all, default)",
        "tool": "get_mp_tradinghours_list_markets",
        "use_common": ["api_token"],
        "params": {},
    })

    # --- TradingHours: Lookup Markets ---
    add_test({
        "name": "TradingHours: Lookup 'NYSE'",
        "tool": "get_mp_tradinghours_lookup_markets",
        "use_common": ["api_token"],
        "params": {
            "q": "NYSE",
        },
    })

    # --- TradingHours: Lookup Markets with group filter ---
    add_test({
        "name": "TradingHours: Lookup 'London' (core)",
        "tool": "get_mp_tradinghours_lookup_markets",
        "use_common": ["api_token"],
        "params": {
            "q": "London",
            "group": "core",
        },
    })

    # --- TradingHours: Market Details ---
    add_test({
        "name": "TradingHours: Market Details us.nyse",
        "tool": "get_mp_tradinghours_market_details",
        "use_common": ["api_token"],
        "params": {
            "fin_id": "us.nyse",
        },
    })

    # --- TradingHours: Market Status ---
    add_test({
        "name": "TradingHours: Market Status us.nyse",
        "tool": "get_mp_tradinghours_market_status",
        "use_common": ["api_token"],
        "params": {
            "fin_id": "us.nyse",
        },
    })

    # =====================================================================
    #  Praams Multi-Factor Reports
    # =====================================================================

    # --- Praams Report Equity by Ticker ---
    add_test({
        "name": "Praams Report Equity by Ticker (AAPL)",
        "tool": "get_mp_praams_report_equity_by_ticker",
        "use_common": ["api_token"],
        "params": {
            "ticker": "AAPL",
            "email": "test@example.com",
        },
    })

    # --- Praams Report Equity by ISIN ---
    add_test({
        "name": "Praams Report Equity by ISIN (US0378331005)",
        "tool": "get_mp_praams_report_equity_by_isin",
        "use_common": ["api_token"],
        "params": {
            "isin": "US0378331005",
            "email": "test@example.com",
        },
    })

    # --- Praams Report Bond by ISIN ---
    add_test({
        "name": "Praams Report Bond by ISIN (US7593518852)",
        "tool": "get_mp_praams_report_bond_by_isin",
        "use_common": ["api_token"],
        "params": {
            "isin": "US7593518852",
            "email": "test@example.com",
        },
    })
