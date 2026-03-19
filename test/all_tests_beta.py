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

