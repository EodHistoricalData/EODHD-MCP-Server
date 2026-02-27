# This module registers all "new" tests cases to facilitate debugging only new features.

def register(add_test, COMMON):
    pass
# --- Praams Bank Income Statement by ISIN ---
#    add_test({
#        "name": "Praams Bank Balance Sheet retrieval by ISIN (US46625H1005)",
#        "tool": "get_mp_praams_bank_balance_sheet_by_isin",
#        "use_common": ["api_token"],
#        "params": {
#            "isin": "US46625H1005",
#        },
#    })

    # --- Marketplace / Praams: Smart Investment Screener (Bond) ---
    add_test({
        "name": "Praams Smart Screener (Bond): curl-equivalent minimal",
        "tool": "get_mp_praams_smart_screener_bond",
        "use_common": ["api_token"],
        "params": {
            "skip": 1,
            "take": 1,
            # JSON body (filters)
            "growthMomMin": 4,
            "growthMomMax": 7,
            "regions": [3],          # Europe
            "sectors": [6],          # Financial Services
            "currency": ["EUR"],
            "marketViewMin": 4,
            "marketViewMax": 7,
            "yieldMin": 7,
            "yieldMax": 15,
        },
    })

    # A “broader” request returning more peers (useful to validate pagination/totalCount)
    add_test({
        "name": "Praams Smart Screener (Bond): wider take=10",
        "tool": "get_mp_praams_smart_screener_bond",
        "use_common": ["api_token"],
        "params": {
            "skip": 0,
            "take": 10,
            "regions": [3],
            "sectors": [6],
            "currency": ["EUR"],
            "growthMomMin": 3,
            "growthMomMax": 7,
            "marketViewMin": 3,
            "marketViewMax": 7,
            "yieldMin": 5,
            "yieldMax": 20,
            # example extra filters (uncomment if you want)
            # "liquidityMin": 2,
            # "liquidityMax": 7,
            # "countryRiskMax": 3,
            # "orderBy": "ratio",
        },
    })

    # Curl-equivalent (exactly as your working example)
    add_test({
        "name": "Praams Smart Screener (Equity): curl-equivalent minimal",
        "tool": "get_mp_praams_smart_screener_equity",
        "use_common": ["api_token"],
        "params": {
            "skip": 0,
            "take": 3,
            "solvencyMin": 1,
            "solvencyMax": 4,
            "countries": [23],  # China
            "sectors": [10],  # Technology
            "dividendsMin": 4,
            "dividendsMax": 7,
        },
    })

    # Broader request (validate pagination / more results)
    add_test({
        "name": "Praams Smart Screener (Equity): broader filters take=10",
        "tool": "get_mp_praams_smart_screener_equity",
        "use_common": ["api_token"],
        "params": {
            "skip": 0,
            "take": 10,
            "countries": [23],
            "sectors": [10],
            "dividendsMin": 3,
            "dividendsMax": 7,
            "solvencyMin": 1,
            "solvencyMax": 5,
            # optional extra filters
            "liquidityMin": 2,
            "liquidityMax": 7,
            "stressTestMax": 7,
            # "orderBy": "ratio",
        },
    })

    # Sanity test: different geography slice (regions + currency)
    add_test({
        "name": "Praams Smart Screener (Equity): regions + currency slice",
        "tool": "get_mp_praams_smart_screener_equity",
        "use_common": ["api_token"],
        "params": {
            "skip": 0,
            "take": 5,
            "regions": [3],  # Europe (per your mapping)
            "currency": ["EUR"],
            "valuationMin": 3,
            "valuationMax": 7,
            "performanceMin": 2,
            "performanceMax": 7,
        },
    })







