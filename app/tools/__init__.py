# app/tools/__init__.py

import importlib
import inspect
import logging
from collections.abc import Callable, Iterable
from typing import Any

from fastmcp.utilities.docstring_parsing import parse_docstring

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
    "get_historical_dividends",
    "get_historical_splits",
    "get_insider_transactions",
    "get_insider_transactions_form4",
    "get_congressional_trades",
    "sec_filings",
    "get_asx_corporate_actions",
    "get_historical_commodity_prices",
    "capture_realtime_ws",
    "get_realtime_minute_bars",
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
    "get_cboe_index_data",
    "get_bulk_fundamentals",
    "get_stock_market_logos",
    "get_stock_market_logos_svg",
    "get_ust_bill_rates",
    "get_ust_yield_rates",
    "get_ust_real_yield_rates",
    "get_ust_long_term_rates",
    "retrieve_description_by_id",
    "get_support_resistance_levels",
    "resolve_ticker",
    # Credit & Sovereign Risk
    "get_credit_sovereign_risk_premium",
    "get_credit_sovereign_credit_ratings",
    "get_credit_sovereign_cds_spreads",
    "get_credit_sovereign_default_spreads",
    "get_credit_corporate_cmdi",
    "get_credit_corporate_hqm_yields",
    "get_credit_cds_market_aggregates",
    # Sanctions / OFAC
    "get_sanctions_entities",
    "get_sanctions_vessels",
    "get_sanctions_programs",
    "get_sanctions_sources",
    # Interest Rates
    "get_rates_reference_rates",
    "get_rates_policy_rates",
    "get_rates_funding_stress",
    # Real Estate Data
    "get_real_estate_countries",
    "get_real_estate_selected_prices",
    "get_real_estate_detailed_prices",
    "get_real_estate_detailed_series",
]

MARKETPLACE_TOOLS: list[str] = [
    "get_mp_us_options_contracts",
    "get_mp_us_options_eod",
    "get_mp_us_options_underlyings",
    "get_mp_indices_list",
    "get_mp_index_components",
    "get_mp_tick_data",
    "get_mp_tradinghours_list_markets",
    "get_mp_tradinghours_lookup_markets",
    "get_mp_tradinghours_market_details",
    "get_mp_tradinghours_market_status",
]

THIRD_PARTY_TOOLS: list[str] = [
    # praams endpoints
    "get_mp_praams_risk_scoring_by_ticker",
    "get_mp_praams_risk_scoring_by_isin",
    "get_mp_praams_bond_analyze_by_isin",
    "get_mp_praams_bank_income_statement_by_ticker",
    "get_mp_praams_bank_income_statement_by_isin",
    "get_mp_praams_bank_balance_sheet_by_ticker",
    "get_mp_praams_bank_balance_sheet_by_isin",
    "get_mp_praams_smart_investment_screener_bond",
    "get_mp_praams_smart_investment_screener_equity",
    "get_mp_praams_report_equity_by_ticker",
    "get_mp_praams_report_equity_by_isin",
    "get_mp_praams_report_bond_by_isin",
    # investverte endpoints
    "get_mp_investverte_esg_list_companies",
    "get_mp_investverte_esg_list_countries",
    "get_mp_investverte_esg_view_country",
    "get_mp_investverte_esg_view_company",
    "get_mp_investverte_esg_list_sectors",
    "get_mp_investverte_esg_view_sector",
]

ALL_TOOLS: list[str] = MAIN_TOOLS + MARKETPLACE_TOOLS + THIRD_PARTY_TOOLS


class _DocstringTools:
    """Hands a tool module the server, keeping tool descriptions as fastmcp 3.4 built them.

    fastmcp 3.4 cut a docstring only at its `Args:` section (the parameters move into the
    input schema) and otherwise kept it whole. fastmcp 4 also cuts at `Returns:`,
    `Examples:` and similar sections, so tools without an `Args:` block would silently
    lose the return-shape and example text written for the agent. For those tools the
    whole docstring is passed as an explicit description.
    """

    def __init__(self, mcp: Any):
        self._mcp = mcp

    def tool(self, *args: Any, **kwargs: Any) -> Any:
        if args and callable(args[0]):
            fn, rest = args[0], args[1:]

            return self._mcp.tool(fn, *rest, **{**_description_kwargs(fn), **kwargs})

        def decorator(fn: Callable[..., Any]) -> Any:
            return self._mcp.tool(*args, **{**_description_kwargs(fn), **kwargs})(fn)

        return decorator

    def __getattr__(self, name: str) -> Any:
        return getattr(self._mcp, name)


def _description_kwargs(fn: Callable[..., Any]) -> dict[str, Any]:
    if parse_docstring(fn).parameters:
        return {}

    return {"description": inspect.getdoc(fn)}


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
        fn(_DocstringTools(mcp))
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
