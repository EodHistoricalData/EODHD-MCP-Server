# app/tools/__init__.py

import importlib
import logging
from typing import Iterable

logger = logging.getLogger("eodhd-mcp.tools")

# --- Tool module names (filenames without .py) ---

MAIN_TOOLS: list[str] = [
    "get_historical_stock_prices",
    "get_live_price_data",
    "get_intraday_historical_data",
    "get_company_news",
    "get_sentiment_data",
    "get_news_word_weights",
    "get_exchanges_list",
    "get_exchange_tickers",
    "get_macro_indicator",
    "get_stocks_from_search",
    "get_user_details",
    "get_exchange_details",
    "get_symbol_change_history",
    "get_historical_market_cap",
    "get_insider_transactions",
    "capture_realtime_ws",
    "get_us_tick_data",
    "get_stock_screener_data",
    "get_economic_events",
    "get_upcoming_earnings",
    "get_earnings_trends",
    "get_upcoming_ipos",
    "get_upcoming_splits",
    "get_upcoming_dividends",
    "get_fundamentals_data",
    "get_technical_indicators",
    "get_us_live_extended_quotes",
    "get_cboe_indices_list",
    "get_cboe_index_data"
]

MARKETPLACE_TOOLS: list[str] = [
    "get_mp_us_options_contracts",
    "get_mp_us_options_eod",
    "get_mp_us_options_underlyings",
    "get_mp_indices_list",
    "get_mp_index_components",
]

THIRD_PARTY_TOOLS: list[str] = [
    #illio endpoints
    "get_mp_illio_performance_insights",
    "get_mp_illio_risk_insights",
    "get_mp_illio_market_insights_performance",
    "get_mp_illio_market_insights_best_worst",
    "get_mp_illio_market_insights_volatility",
    "get_mp_illio_market_insights_risk_return",
    "get_mp_illio_market_insights_largest_volatility",
    "get_mp_illio_market_insights_beta_bands",
    #praams endpoints
    "get_mp_praams_risk_scoring_by_ticker",
    "get_mp_praams_risk_scoring_by_isin",
    "get_mp_praams_bond_analyze_by_isin",
    "get_mp_praams_bank_income_statement_by_ticker",
    "get_mp_praams_bank_income_statement_by_isin",
    "get_mp_praams_bank_balance_sheet_by_ticker",
    "get_mp_praams_bank_balance_sheet_by_isin",
    #investverte endpoints
    "get_mp_investverte_esg_list_companies",
    "get_mp_investverte_esg_list_countries",
    "get_mp_investverte_esg_view_country",
    "get_mp_investverte_esg_view_company",
    "get_mp_investverte_esg_list_sectors",
    "get_mp_investverte_esg_view_sector"

]

ALL_TOOLS: list[str] = MAIN_TOOLS + MARKETPLACE_TOOLS + THIRD_PARTY_TOOLS


def _safe_register(mcp, module_name: str, attr: str = "register") -> None:
    """
    Import .{module_name} and call its register(mcp), logging and skipping on errors.
    """
    try:
        mod = importlib.import_module(f".{module_name}", package=__name__)
    except ModuleNotFoundError as e:
        logger.warning("Skipping tool '%s': module not found (%s)", module_name, e)
        return
    except Exception as e:
        logger.error("Error importing tool '%s': %s: %s", module_name, type(e).__name__, e)
        return

    fn = getattr(mod, attr, None)
    if not callable(fn):
        logger.warning("Skipping tool '%s': no callable '%s()' found", module_name, attr)
        return

    try:
        fn(mcp)
        logger.info("Registered tool: %s.%s", module_name, attr)
    except Exception as e:
        logger.error("Failed to register tool '%s': %s: %s", module_name, type(e).__name__, e)


def _dedupe(seq: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in seq:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def register_all(mcp) -> None:
    """Attempt to register every known tool, skipping any that are missing or erroring."""
    for name in _dedupe(ALL_TOOLS):
        _safe_register(mcp, name)
