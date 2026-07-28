# tests/auto/test_tools.py
"""Parametrized auto for all tool files.

Covers:
  1. URL construction — mock make_request, verify URL path + query params
  2. Input validation — invalid inputs raise ToolError
  3. Error responses — None / {error: ...} from API handled correctly
"""

import asyncio
import json
import socket
from unittest.mock import AsyncMock, patch

import pytest
from app.tools import register_all
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

# ---------------------------------------------------------------------------
# FastMCP compatibility — method names differ across versions
# ---------------------------------------------------------------------------


async def _invoke_tool(mcp, name, args):
    """Call a tool on the FastMCP instance, compatible with all versions."""
    if hasattr(mcp, "call_tool"):
        result = await mcp.call_tool(name, args)
    else:
        result = await mcp._call_tool(name, args)
    # Older versions return an object with .content; newer return list directly
    if hasattr(result, "content"):
        return list(result.content)
    return list(result)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

API_SUCCESS = {"ok": True}

# Tools that expect bytes from make_request (response_mode="bytes")
_BYTES_TOOLS = {
    "get_stock_market_logos",
    "get_mp_praams_report_bond_by_isin",
    "get_mp_praams_report_equity_by_isin",
    "get_mp_praams_report_equity_by_ticker",
}
# Tools that expect str from make_request (SVG text)
_TEXT_TOOLS = {
    "get_stock_market_logos_svg",
}


def _default_mock_return(mock_module: str) -> object:
    """Return an appropriate mock value based on the tool's expected response type."""
    if mock_module in _BYTES_TOOLS:
        return b"\x89PNG fake image data"
    if mock_module in _TEXT_TOOLS:
        return "<svg>manual</svg>"
    if mock_module == "resolve_ticker":
        return [{"Code": "AAPL", "Exchange": "US", "Name": "Apple Inc.", "ISIN": "US0378331005", "Type": "stock"}]
    return API_SUCCESS


@pytest.fixture(scope="module")
def mcp():
    """Register all tools once for the module."""
    server = FastMCP("manual")
    register_all(server)
    return server


def _mock_path(module_name: str) -> str:
    """Return the mock target for make_request in a tool module."""
    return f"app.tools.{module_name}.make_request"


async def _call(mcp, tool_name, args, mock_module, mock_return=None):
    """Call a tool with mocked make_request, return (result_text, mock)."""
    target = _mock_path(mock_module)
    ret = mock_return if mock_return is not None else _default_mock_return(mock_module)
    mock = AsyncMock(return_value=ret)
    with patch(target, mock):
        result = await _invoke_tool(mcp, tool_name, args)
    # _call_tool returns list[EmbeddedResource] directly
    content = result[0]
    # Tools return EmbeddedResource — text for JSON/XML/CSV, blob for binary (PNG, PDF)
    resource = content.resource if hasattr(content, "resource") else content
    text = getattr(resource, "text", None) or getattr(resource, "blob", "")
    return text, mock


# ---------------------------------------------------------------------------
# 1. URL construction — valid inputs → correct API URL
# ---------------------------------------------------------------------------

# (tool_name, args, mock_module, expected_url_fragments)
URL_CASES = [
    # Core endpoints
    ("get_exchanges_list", {}, "get_exchanges_list", ["/exchanges-list/", "fmt=json"]),
    ("get_exchange_tickers", {"exchange_code": "US"}, "get_exchange_tickers", ["/exchange-symbol-list/US", "fmt=json"]),
    (
        "get_historical_stock_prices",
        {"ticker": "AAPL.US"},
        "get_historical_stock_prices",
        ["/eod/AAPL.US", "period=d", "fmt=json"],
    ),
    (
        "get_historical_stock_prices",
        {"ticker": "AAPL.US", "period": "m", "order": "d"},
        "get_historical_stock_prices",
        ["/eod/AAPL.US", "period=m", "order=d"],
    ),
    ("get_live_price_data", {"ticker": "AAPL.US"}, "get_live_price_data", ["/real-time/AAPL.US", "fmt=json"]),
    # get_fundamentals_data excluded: multi-request tool, tested separately below
    ("get_company_news", {"ticker": "AAPL.US"}, "get_company_news", ["/news", "s=AAPL.US"]),
    ("get_sentiment_data", {"symbols": "AAPL.US"}, "get_sentiment_data", ["/sentiments", "s=AAPL.US"]),
    ("get_macro_indicator", {"country": "USA"}, "get_macro_indicator", ["/macro-indicator/USA"]),
    ("get_user_details", {}, "get_user_details", ["/user"]),
    ("get_bulk_fundamentals", {"exchange": "US"}, "get_bulk_fundamentals", ["/bulk-fundamentals/US", "fmt=json"]),
    ("stock_screener", {}, "get_stock_screener_data", ["/screener"]),
    # Search / symbol tools
    ("get_stocks_from_search", {"query": "apple"}, "get_stocks_from_search", ["/search/apple"]),
    ("get_symbol_change_history", {}, "get_symbol_change_history", ["/symbol-change-history"]),
    ("get_historical_dividends", {"ticker": "AAPL.US"}, "get_historical_dividends", ["/div/AAPL.US", "fmt=json"]),
    ("get_historical_splits", {"ticker": "AAPL.US"}, "get_historical_splits", ["/splits/AAPL.US", "fmt=json"]),
    ("resolve_ticker", {"query": "apple"}, "resolve_ticker", ["/search/apple", "fmt=json"]),
    # Calendar endpoints
    ("get_upcoming_earnings", {}, "get_upcoming_earnings", ["/calendar/earnings"]),
    ("get_upcoming_ipos", {}, "get_upcoming_ipos", ["/calendar/ipos"]),
    ("get_upcoming_dividends", {"symbol": "AAPL.US"}, "get_upcoming_dividends", ["/calendar/dividends"]),
    ("get_upcoming_splits", {}, "get_upcoming_splits", ["/calendar/splits"]),
    ("get_earnings_trends", {"symbols": "AAPL.US"}, "get_earnings_trends", ["/calendar/trend"]),
    ("get_economic_events", {}, "get_economic_events", ["/economic-events"]),
    # Exchange details
    ("get_exchange_details", {"exchange_code": "US"}, "get_exchange_details", ["/exchange-details/US"]),
    # Historical data
    (
        "get_historical_market_cap",
        {"ticker": "AAPL.US"},
        "get_historical_market_cap",
        ["/historical-market-cap/AAPL.US"],
    ),
    ("get_insider_transactions", {"symbol": "AAPL.US"}, "get_insider_transactions", ["/insider-transactions"]),
    (
        "get_congressional_trades",
        {"chamber": "senate", "transaction_type": "purchase,sale"},
        "get_congressional_trades",
        ["/congressional-trades", "chamber=senate"],
    ),
    # Technical
    (
        "get_technical_indicators",
        {"ticker": "AAPL.US", "function": "sma"},
        "get_technical_indicators",
        ["/technical/AAPL.US", "function=sma"],
    ),
    # News
    ("get_news_word_weights", {"ticker": "AAPL.US"}, "get_news_word_weights", ["/news-word-weights", "s=AAPL.US"]),
    # Logos
    ("get_stock_market_logos", {"symbol": "AAPL.US"}, "get_stock_market_logos", ["/logo/AAPL.US"]),
    ("get_stock_market_logos_svg", {"symbol": "AAPL.US"}, "get_stock_market_logos_svg", ["/logo-svg/AAPL.US"]),
    # US market
    ("get_us_live_extended_quotes", {"symbols": "AAPL.US"}, "get_us_live_extended_quotes", ["/us-quote-delayed"]),
    (
        "get_us_tick_data",
        {"ticker": "AAPL.US", "from_timestamp": 1694455200, "to_timestamp": 1694541600},
        "get_us_tick_data",
        ["/ticks/", "s=AAPL.US"],
    ),
    # CBOE
    (
        "get_cboe_index_data",
        {"index_code": "BDE30P", "feed_type": "snapshot_official_closing", "date": "2017-02-01"},
        "get_cboe_index_data",
        ["/cboe/index"],
    ),
    ("get_cboe_indices_list", {}, "get_cboe_indices_list", ["/cboe/"]),
    # Treasury
    ("get_ust_bill_rates", {}, "get_ust_bill_rates", ["/ust/bill-rates"]),
    ("get_ust_long_term_rates", {}, "get_ust_long_term_rates", ["/ust/long-term-rates"]),
    ("get_ust_real_yield_rates", {}, "get_ust_real_yield_rates", ["/ust/real-yield-rates"]),
    ("get_ust_yield_rates", {}, "get_ust_yield_rates", ["/ust/yield-rates"]),
    # Real Estate (BIS property prices)
    ("get_real_estate_countries", {}, "get_real_estate_countries", ["/real-estate/countries", "fmt=json"]),
    (
        "get_real_estate_selected_prices",
        {"code": "us", "type": "real", "metric": "index"},
        "get_real_estate_selected_prices",
        ["/real-estate/US", "filter[type]=real", "filter[metric]=index"],
    ),
    (
        "get_real_estate_detailed_prices",
        {"code": "AE", "property_type": "1"},
        "get_real_estate_detailed_prices",
        ["/real-estate/AE/detailed", "filter[property_type]=1"],
    ),
    (
        "get_real_estate_detailed_series",
        {"code": "us"},
        "get_real_estate_detailed_series",
        ["/real-estate/US/detailed/series"],
    ),
    # Intraday
    ("get_intraday_historical_data", {"ticker": "AAPL.US"}, "get_intraday_historical_data", ["/intraday/AAPL.US"]),
    # Marketplace — indices
    ("mp_index_components", {"symbol": "GSPC.INDX"}, "get_mp_index_components", ["/mp/unicornbay/spglobal/comp/"]),
    ("mp_indices_list", {}, "get_mp_indices_list", ["/mp/unicornbay/spglobal/list"]),
    # Marketplace — ESG
    (
        "get_mp_investverte_esg_list_companies",
        {},
        "get_mp_investverte_esg_list_companies",
        ["/mp/investverte/companies"],
    ),
    (
        "get_mp_investverte_esg_list_countries",
        {},
        "get_mp_investverte_esg_list_countries",
        ["/mp/investverte/countries"],
    ),
    ("get_mp_investverte_esg_list_sectors", {}, "get_mp_investverte_esg_list_sectors", ["/mp/investverte/sectors"]),
    (
        "get_mp_investverte_esg_view_company",
        {"symbol": "AAPL"},
        "get_mp_investverte_esg_view_company",
        ["/mp/investverte/esg/AAPL"],
    ),
    (
        "get_mp_investverte_esg_view_country",
        {"symbol": "US"},
        "get_mp_investverte_esg_view_country",
        ["/mp/investverte/country/US"],
    ),
    (
        "get_mp_investverte_esg_view_sector",
        {"symbol": "Airlines"},
        "get_mp_investverte_esg_view_sector",
        ["/mp/investverte/sector/Airlines"],
    ),
    # Marketplace — PRAAMS
    (
        "get_mp_praams_bank_balance_sheet_by_isin",
        {"isin": "US0378331005"},
        "get_mp_praams_bank_balance_sheet_by_isin",
        ["/mp/praams/bank/balance_sheet/isin/"],
    ),
    (
        "get_mp_praams_bank_balance_sheet_by_ticker",
        {"ticker": "AAPL.US"},
        "get_mp_praams_bank_balance_sheet_by_ticker",
        ["/mp/praams/bank/balance_sheet/ticker/"],
    ),
    (
        "get_mp_praams_bank_income_statement_by_isin",
        {"isin": "US0378331005"},
        "get_mp_praams_bank_income_statement_by_isin",
        ["/mp/praams/bank/income_statement/isin/"],
    ),
    (
        "get_mp_praams_bank_income_statement_by_ticker",
        {"ticker": "AAPL.US"},
        "get_mp_praams_bank_income_statement_by_ticker",
        ["/mp/praams/bank/income_statement/ticker/"],
    ),
    (
        "get_mp_praams_bond_analyze_by_isin",
        {"isin": "US0378331005"},
        "get_mp_praams_bond_analyze_by_isin",
        ["/mp/praams/analyse/bond/"],
    ),
    (
        "get_mp_praams_report_bond_by_isin",
        {"isin": "US0378331005", "email": "manual@manual.com"},
        "get_mp_praams_report_bond_by_isin",
        ["/mp/praams/reports/bond/"],
    ),
    (
        "get_mp_praams_report_equity_by_isin",
        {"isin": "US0378331005", "email": "manual@manual.com"},
        "get_mp_praams_report_equity_by_isin",
        ["/mp/praams/reports/equity/isin/"],
    ),
    (
        "get_mp_praams_report_equity_by_ticker",
        {"ticker": "AAPL.US", "email": "manual@manual.com"},
        "get_mp_praams_report_equity_by_ticker",
        ["/mp/praams/reports/equity/ticker/"],
    ),
    (
        "get_mp_praams_risk_scoring_by_isin",
        {"isin": "US0378331005"},
        "get_mp_praams_risk_scoring_by_isin",
        ["/mp/praams/analyse/equity/isin/"],
    ),
    (
        "get_mp_praams_risk_scoring_by_ticker",
        {"ticker": "AAPL.US"},
        "get_mp_praams_risk_scoring_by_ticker",
        ["/mp/praams/analyse/equity/ticker/"],
    ),
    (
        "get_mp_praams_smart_screener_equity",
        {"countries": [1]},
        "get_mp_praams_smart_investment_screener_equity",
        ["/mp/praams/explore/equity"],
    ),
    (
        "get_mp_praams_smart_screener_bond",
        {"countries": [1]},
        "get_mp_praams_smart_investment_screener_bond",
        ["/mp/praams/explore/bond"],
    ),
    # Marketplace — tick data & options
    ("get_mp_tick_data", {"ticker": "AAPL.US"}, "get_mp_tick_data", ["/mp/unicornbay/tickdata/ticks", "s=AAPL.US"]),
    ("get_us_options_contracts", {}, "get_mp_us_options_contracts", ["/mp/unicornbay/options/contracts"]),
    ("get_us_options_eod", {}, "get_mp_us_options_eod", ["/mp/unicornbay/options/eod"]),
    ("get_us_options_underlyings", {}, "get_mp_us_options_underlyings", ["/mp/unicornbay/options/underlying-symbols"]),
    # Marketplace — trading hours
    ("get_mp_tradinghours_list_markets", {}, "get_mp_tradinghours_list_markets", ["/mp/tradinghours/markets"]),
    (
        "get_mp_tradinghours_lookup_markets",
        {"q": "NYSE"},
        "get_mp_tradinghours_lookup_markets",
        ["/mp/tradinghours/markets/lookup"],
    ),
    (
        "get_mp_tradinghours_market_details",
        {"fin_id": "us.nyse"},
        "get_mp_tradinghours_market_details",
        ["/mp/tradinghours/markets/details"],
    ),
    (
        "get_mp_tradinghours_market_status",
        {"fin_id": "us.nyse"},
        "get_mp_tradinghours_market_status",
        ["/mp/tradinghours/markets/status"],
    ),
    # Credit & Sovereign Risk — bracketed filter[...] keys
    (
        "get_credit_sovereign_risk_premium",
        {"country": "USA", "region": "North America", "as_of": "2025-01-01", "limit": 50, "offset": 20},
        "get_credit_sovereign_risk_premium",
        [
            "/credit-risk/sovereign/risk-premium",
            "filter[country]=USA",
            "filter[region]=North+America",
            "filter[as_of]=2025-01-01",
            "page[limit]=50",
            "page[offset]=20",
        ],
    ),
    (
        "get_credit_sovereign_credit_ratings",
        {"country": "DEU", "as_of": "2025-01-01"},
        "get_credit_sovereign_credit_ratings",
        ["/credit-risk/sovereign/credit-ratings", "filter[country]=DEU", "filter[as_of]=2025-01-01"],
    ),
    (
        "get_credit_sovereign_cds_spreads",
        {"country": "ITA"},
        "get_credit_sovereign_cds_spreads",
        ["/credit-risk/sovereign/cds-spreads", "filter[country]=ITA"],
    ),
    (
        "get_credit_sovereign_default_spreads",
        {"rating": "Baa2"},
        "get_credit_sovereign_default_spreads",
        ["/credit-risk/sovereign/default-spreads", "filter[rating]=Baa2"],
    ),
    (
        "get_credit_corporate_cmdi",
        {"date_from": "2025-01-01", "date_to": "2025-12-31"},
        "get_credit_corporate_cmdi",
        ["/credit-risk/corporate/cmdi", "filter[from]=2025-01-01", "filter[to]=2025-12-31"],
    ),
    (
        "get_credit_corporate_hqm_yields",
        {"tenor": 10, "type": "spot"},
        "get_credit_corporate_hqm_yields",
        ["/credit-risk/corporate/hqm-yields", "filter[tenor]=10", "filter[type]=spot"],
    ),
    (
        "get_credit_cds_market_aggregates",
        {"metric": "gross_notional", "dimension": "grade", "value": "IG", "region": "Europe"},
        "get_credit_cds_market_aggregates",
        [
            "/credit-risk/cds-market/aggregates",
            "filter[metric]=gross_notional",
            "filter[dimension]=grade",
            "filter[value]=IG",
            "filter[region]=Europe",
        ],
    ),
    # Sanctions — BARE keys (NOT filter[...]); pagination still uses page[...]
    (
        "get_sanctions_entities",
        {"source": "ofac", "type": "individual", "program": "UKRAINE-EO13662", "country": "Russia", "active": True},
        "get_sanctions_entities",
        [
            "/sanctions/entities",
            "source=ofac",
            "type=individual",
            "program=UKRAINE-EO13662",
            "country=Russia",
            "active=true",
        ],
    ),
    (
        "get_sanctions_vessels",
        {"source": "ofac", "imo": "9160670", "flag": "Panama", "vessel_type": "Crude Oil Tanker"},
        "get_sanctions_vessels",
        ["/sanctions/vessels", "source=ofac", "imo=9160670", "flag=Panama", "vessel_type=Crude+Oil+Tanker"],
    ),
    (
        "get_sanctions_programs",
        {},
        "get_sanctions_programs",
        ["/sanctions/programs"],
    ),
    (
        "get_sanctions_sources",
        {},
        "get_sanctions_sources",
        ["/sanctions/sources"],
    ),
    # Interest Rates — bracketed filter[...] keys
    (
        "get_rates_reference_rates",
        {"code": "SOFR", "currency": "USD", "date_from": "2025-01-01", "date_to": "2025-06-30"},
        "get_rates_reference_rates",
        [
            "/rates/reference-rates",
            "filter[code]=SOFR",
            "filter[currency]=USD",
            "filter[from]=2025-01-01",
            "filter[to]=2025-06-30",
        ],
    ),
    (  # comma-separated currency accepted (upstream CsvIn)
        "get_rates_reference_rates",
        {"currency": "usd,eur"},
        "get_rates_reference_rates",
        ["/rates/reference-rates", "filter[currency]=USD%2CEUR"],
    ),
    (
        "get_rates_policy_rates",
        {"country": "US", "central_bank": "FED"},
        "get_rates_policy_rates",
        ["/rates/policy-rates", "filter[country]=US", "filter[central_bank]=FED"],
    ),
    (  # comma-separated tenor/type accepted (upstream CsvIn)
        "get_credit_corporate_hqm_yields",
        {"tenor": "5,10", "type": "spot,par"},
        "get_credit_corporate_hqm_yields",
        ["/credit-risk/corporate/hqm-yields", "filter[tenor]=5%2C10", "filter[type]=spot%2Cpar"],
    ),
    (
        "get_rates_funding_stress",
        {"code": "EFFR_SOFR", "date_from": "2025-01-01"},
        "get_rates_funding_stress",
        ["/spreads/funding-stress", "filter[code]=EFFR_SOFR", "filter[from]=2025-01-01"],
    ),
    (  # flexible date input is coerced to YYYY-MM-DD before it reaches the API
        "get_credit_corporate_cmdi",
        {"date_from": "2025/01/02", "date_to": "Mar 4, 2025"},
        "get_credit_corporate_cmdi",
        ["/credit-risk/corporate/cmdi", "filter[from]=2025-01-02", "filter[to]=2025-03-04"],
    ),
    (  # as_of is coerced the same way
        "get_credit_sovereign_cds_spreads",
        {"as_of": "30/06/2025"},
        "get_credit_sovereign_cds_spreads",
        ["/credit-risk/sovereign/cds-spreads", "filter[as_of]=2025-06-30"],
    ),
    (  # code CSVs are trimmed and upper-cased (upstream validates element-wise)
        "get_rates_policy_rates",
        {"code": "fed_target_lower, ecb_dfr", "central_bank": "fed", "country": "us"},
        "get_rates_policy_rates",
        [
            "/rates/policy-rates",
            "filter[code]=FED_TARGET_LOWER%2CECB_DFR",
            "filter[central_bank]=FED",
            "filter[country]=US",
        ],
    ),
    (
        "get_rates_funding_stress",
        {"code": "effr_sofr, obfr_effr"},
        "get_rates_funding_stress",
        ["/spreads/funding-stress", "filter[code]=EFFR_SOFR%2COBFR_EFFR"],
    ),
    (
        "get_rates_reference_rates",
        {"code": "sofrindex"},
        "get_rates_reference_rates",
        ["/rates/reference-rates", "filter[code]=SOFRINDEX"],
    ),
]

# Endpoints whose proxy controllers forward no pagination params at all.
NON_PAGINATED_CASES = [
    ("get_rates_funding_stress", {"code": "EFFR_SOFR"}, "get_rates_funding_stress"),
    ("get_sanctions_programs", {}, "get_sanctions_programs"),
    ("get_sanctions_sources", {}, "get_sanctions_sources"),
    # UST endpoints ignore page[limit]/page[offset]/from/to; only filter[year] applies.
    ("get_ust_yield_rates", {}, "get_ust_yield_rates"),
    ("get_ust_bill_rates", {}, "get_ust_bill_rates"),
    ("get_ust_real_yield_rates", {}, "get_ust_real_yield_rates"),
    ("get_ust_long_term_rates", {}, "get_ust_long_term_rates"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name,args,mock_module,url_fragments", URL_CASES, ids=[c[0] for c in URL_CASES])
async def test_url_construction(mcp, tool_name, args, mock_module, url_fragments):
    """Tool builds correct URL with expected path and query params."""
    _text, mock = await _call(mcp, tool_name, args, mock_module)
    assert mock.call_count >= 1
    url = str(mock.call_args_list[0].args[0])
    for frag in url_fragments:
        assert frag in url, f"Expected '{frag}' in URL: {url}"


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name,args,mock_module", NON_PAGINATED_CASES, ids=[c[0] for c in NON_PAGINATED_CASES])
async def test_no_pagination_params(mcp, tool_name, args, mock_module):
    """Endpoints without upstream pagination must not send page[...] params."""
    _text, mock = await _call(mcp, tool_name, args, mock_module)
    url = str(mock.call_args_list[0].args[0])
    assert "page[limit]" not in url, f"Unexpected page[limit] in URL: {url}"
    assert "page[offset]" not in url, f"Unexpected page[offset] in URL: {url}"
    assert "fmt=" not in url, f"Unexpected fmt in URL: {url}"


# ---------------------------------------------------------------------------
# 2. Input validation — invalid inputs raise ToolError
# ---------------------------------------------------------------------------

# (tool_name, bad_args, error_match)
VALIDATION_CASES = [
    # Ticker validation
    ("get_historical_stock_prices", {"ticker": ""}, "required"),
    ("get_live_price_data", {"ticker": ""}, "required"),
    ("get_fundamentals_data", {"ticker": ""}, "required"),
    ("get_historical_market_cap", {"ticker": ""}, "required"),
    ("get_historical_dividends", {"ticker": ""}, "required"),
    ("get_historical_splits", {"ticker": ""}, "required"),
    ("get_technical_indicators", {"ticker": "", "function": "sma"}, "required"),
    # Exchange validation
    ("get_exchange_tickers", {"exchange_code": ""}, "required"),
    ("get_bulk_fundamentals", {"exchange": ""}, "required"),
    # Format validation
    ("get_exchanges_list", {"fmt": "xml"}, "json"),
    ("get_historical_stock_prices", {"ticker": "AAPL.US", "fmt": "xml"}, "(?i)format|json|csv"),
    ("get_historical_dividends", {"ticker": "AAPL.US", "fmt": "xml"}, "(?i)json"),
    ("get_historical_splits", {"ticker": "AAPL.US", "fmt": "xml"}, "(?i)json"),
    # Period/order validation
    ("get_historical_stock_prices", {"ticker": "AAPL.US", "period": "x"}, "(?i)period|must be"),
    ("get_historical_stock_prices", {"ticker": "AAPL.US", "order": "x"}, "(?i)order|must be"),
    # Technical indicators — function required
    ("get_technical_indicators", {"ticker": "AAPL.US", "function": "invalid_fn"}, "(?i)function|supported|invalid"),
    # Macro — country required
    ("get_macro_indicator", {"country": ""}, "(?i)country|required|empty"),
    # Sentiment — symbols required
    ("get_sentiment_data", {"symbols": ""}, "required"),
    # Company news — needs ticker or tag
    ("get_company_news", {}, "(?i)ticker|tag|required|at least"),
    # Resolve ticker — query required
    ("resolve_ticker", {"query": ""}, "(?i)query|required|empty"),
    # Bulk fundamentals — limit range
    ("get_bulk_fundamentals", {"exchange": "US", "limit": 0}, "(?i)limit|range|between|must be"),
    ("get_bulk_fundamentals", {"exchange": "US", "limit": 501}, "(?i)limit|range|between|must be"),
    # Intraday — interval validation
    ("get_intraday_historical_data", {"ticker": "AAPL.US", "interval": "2m"}, "(?i)interval|must be|supported"),
    # Tick data — ticker required
    ("get_mp_tick_data", {"ticker": ""}, "required"),
    # Economic events — comparison validation
    ("get_economic_events", {"comparison": "invalid"}, "(?i)comparison|must be|invalid"),
    # Options — type validation
    ("get_us_options_contracts", {"type": "invalid"}, "(?i)type|must be|invalid"),
    # Live price — additional_symbols too many (>20)
    (
        "get_live_price_data",
        {"ticker": "AAPL.US", "additional_symbols": [f"T{i}.US" for i in range(21)]},
        "(?i)additional|symbols|maximum|20|too many",
    ),
    # URL-breaking ticker / symbol validation
    ("get_news_word_weights", {"ticker": "AAPL/US"}, "(?i)ticker|break the request url"),
    ("get_sentiment_data", {"symbols": "AAPL.US,MSFT/US"}, "(?i)symbols|break the request url"),
    ("get_insider_transactions", {"symbol": "AAPL/US"}, "(?i)symbol|break the request url"),
    ("get_company_news", {"ticker": "AAPL/US"}, "(?i)ticker|break the request url"),
    ("get_historical_market_cap", {"ticker": "AAPL/US"}, "(?i)ticker|break the request url"),
    ("get_historical_dividends", {"ticker": "AAPL/US"}, "(?i)ticker|break the request url"),
    ("get_historical_splits", {"ticker": "AAPL/US"}, "(?i)ticker|break the request url"),
    (
        "get_live_price_data",
        {"ticker": "AAPL.US", "additional_symbols": ["MSFT/US"]},
        "(?i)additional_symbols|break the request url",
    ),
    ("get_upcoming_dividends", {"symbol": "AAPL/US", "date_eq": "2026-03-15"}, "(?i)symbol|break the request url"),
    ("get_upcoming_earnings", {"symbols": ["AAPL.US", "MSFT/US"]}, "(?i)symbols|break the request url"),
    ("get_earnings_trends", {"symbols": ["AAPL.US", "MSFT/US"]}, "(?i)symbols|break the request url"),
    (
        "get_us_tick_data",
        {"ticker": "AAPL/US", "from_timestamp": 1, "to_timestamp": 2},
        "(?i)ticker|break the request url",
    ),
    ("get_mp_tick_data", {"ticker": "AAPL/US"}, "(?i)ticker|break the request url"),
    ("get_stock_market_logos", {"symbol": "AAPL/US"}, "(?i)symbol|break the request url"),
    ("get_stocks_from_search", {"query": "apple", "exchange": "U/S"}, "(?i)exchange|break the request url"),
    ("resolve_ticker", {"query": "apple", "preferred_exchange": "U/S"}, "(?i)preferred_exchange|break the request url"),
    ("get_us_options_contracts", {"underlying_symbol": "AAPL/US"}, "(?i)underlying_symbol|break the request url"),
    ("get_us_options_eod", {"contract": "AAPL/US"}, "(?i)contract|break the request url"),
    ("get_mp_investverte_esg_view_company", {"symbol": "AAPL/US"}, "(?i)symbol|break the request url"),
    # Real Estate — code required, enum + fmt + pagination validation, URL-breaking code
    ("get_real_estate_selected_prices", {"code": ""}, "required"),
    ("get_real_estate_detailed_prices", {"code": ""}, "required"),
    ("get_real_estate_detailed_series", {"code": ""}, "required"),
    ("get_real_estate_selected_prices", {"code": "US", "type": "bogus"}, "(?i)type|invalid"),
    ("get_real_estate_selected_prices", {"code": "US", "metric": "bogus"}, "(?i)metric|invalid"),
    ("get_real_estate_detailed_prices", {"code": "US", "freq": "X"}, "(?i)freq|invalid"),
    ("get_real_estate_countries", {"fmt": "xml"}, "(?i)fmt|json|csv"),
    ("get_real_estate_countries", {"limit": 501}, "(?i)limit|between|must be"),
    ("get_real_estate_countries", {"offset": -1}, "(?i)offset|non-negative|must be"),
    ("get_real_estate_selected_prices", {"code": "US/X"}, "(?i)code|break the request url"),
    # WebSocket — invalid feed
    ("capture_realtime_ws", {"feed": "invalid_feed", "symbols": "AAPL"}, "(?i)feed|must be|invalid|supported"),
    # Stock screener — limit range
    ("stock_screener", {"limit": 0}, "(?i)limit|range|between|must be"),
    ("stock_screener", {"limit": 101}, "(?i)limit|range|between|must be"),
    # CBOE — all 3 params required
    (
        "get_cboe_index_data",
        {"index_code": "", "feed_type": "x", "date": "2017-01-01"},
        "(?i)index_code|required|empty",
    ),
    # Credit & Sovereign Risk — limit / offset / enum / date validation
    ("get_credit_sovereign_risk_premium", {"limit": 0}, "(?i)limit|positive"),
    ("get_credit_sovereign_risk_premium", {"limit": "abc"}, "(?i)limit|positive"),
    ("get_credit_sovereign_risk_premium", {"as_of": "not-a-date"}, "(?i)as_of|date"),
    ("get_credit_sovereign_risk_premium", {"limit": 101}, "(?i)limit|100"),
    ("get_credit_sovereign_risk_premium", {"offset": -1}, "(?i)offset|non-negative"),
    ("get_credit_corporate_hqm_yields", {"tenor": 4}, "(?i)tenor|one of"),
    ("get_credit_corporate_hqm_yields", {"type": "invalid"}, "(?i)type|one of"),
    ("get_credit_cds_market_aggregates", {"metric": "invalid"}, "(?i)metric|one of"),
    ("get_credit_cds_market_aggregates", {"dimension": "invalid"}, "(?i)dimension|one of"),
    # Sanctions — enum / query-length / limit validation
    ("get_sanctions_entities", {"type": "invalid"}, "(?i)type|one of"),
    ("get_sanctions_entities", {"q": "a"}, "(?i)'q'|characters"),
    ("get_sanctions_entities", {"limit": 101}, "(?i)limit|100"),
    ("get_sanctions_vessels", {"q": "a"}, "(?i)'q'|characters"),
    ("get_rates_reference_rates", {"currency": "USD,JPY"}, "(?i)currency|one of"),
    ("get_credit_corporate_hqm_yields", {"tenor": "5,4"}, "(?i)tenor|one of"),
    # Interest Rates — enum / limit / date validation
    ("get_rates_reference_rates", {"currency": "JPY"}, "(?i)currency|one of"),
    ("get_rates_reference_rates", {"limit": 101}, "(?i)limit|100"),
    ("get_rates_policy_rates", {"offset": -1}, "(?i)offset|non-negative"),
    ("get_rates_reference_rates", {"date_from": "not-a-date"}, "(?i)date_from|date"),
    (
        "get_rates_reference_rates",
        {"date_from": "2025-12-31", "date_to": "2025-01-01"},
        "(?i)date_from.*date_to|cannot be after",
    ),
    (
        "get_credit_corporate_cmdi",
        {"date_from": "2025-12-31", "date_to": "2025-01-01"},
        "(?i)date_from.*date_to|cannot be after",
    ),
    (
        "get_rates_funding_stress",
        {"date_from": "2025-12-31", "date_to": "2025-01-01"},
        "(?i)date_from.*date_to|cannot be after",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name,bad_args,error_match",
    VALIDATION_CASES,
    ids=[f"{c[0]}({list(c[1].keys())})" for c in VALIDATION_CASES],
)
async def test_validation_rejects_bad_input(mcp, tool_name, bad_args, error_match):
    """Tool raises ToolError on invalid input."""
    with pytest.raises(ToolError, match=error_match):
        await _invoke_tool(mcp, tool_name, bad_args)


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_mp_investverte_esg_view_sector_encodes_path_segments(mcp):
    _text, mock = await _call(
        mcp,
        "get_mp_investverte_esg_view_sector",
        {"symbol": "Aerospace & Defense"},
        "get_mp_investverte_esg_view_sector",
    )
    url = str(mock.call_args_list[0].args[0])
    assert "/mp/investverte/sector/Aerospace%20%26%20Defense" in url


async def test_capture_realtime_ws_uses_connect_timeout_for_open_timeout(mcp):
    mock_ws = AsyncMock()
    mock_ws.recv = AsyncMock(side_effect=TimeoutError)
    connect_mock = AsyncMock(return_value=mock_ws)

    with patch("app.tools.capture_realtime_ws.websockets.connect", connect_mock):
        result = await _invoke_tool(
            mcp,
            "capture_realtime_ws",
            {
                "feed": "crypto",
                "symbols": "BTC-USD",
                "duration_seconds": 1,
                "connect_timeout": 7.5,
            },
        )

    connect_mock.assert_awaited_once()
    call_kwargs = connect_mock.call_args
    url = call_kwargs.args[0]
    assert "wss://ws.eodhistoricaldata.com/ws/crypto?api_token=" in url
    assert call_kwargs.kwargs["open_timeout"] == 7.5
    assert call_kwargs.kwargs["close_timeout"] == 5
    assert call_kwargs.kwargs["max_queue"] == 1024
    mock_ws.send.assert_awaited()
    mock_ws.close.assert_awaited_once()
    # _call_tool returns list[EmbeddedResource] directly
    content = result[0]
    text = content.resource.text if hasattr(content, "resource") else content.text
    parsed = json.loads(text)
    assert parsed["feed"] == "crypto"


@pytest.mark.asyncio
async def test_capture_realtime_ws_timeout_has_specific_message(mcp):
    connect_mock = AsyncMock(side_effect=asyncio.TimeoutError())

    with (
        patch("app.tools.capture_realtime_ws.websockets.connect", connect_mock),
        pytest.raises(
            ToolError,
            match=r"Timed out while establishing WebSocket connection to ws\.eodhistoricaldata\.com after 3\.0 seconds\.",
        ),
    ):
        await _invoke_tool(
            mcp,
            "capture_realtime_ws",
            {
                "feed": "us_trades",
                "symbols": "AAPL",
                "connect_timeout": 3.0,
            },
        )


@pytest.mark.asyncio
async def test_capture_realtime_ws_dns_error_has_specific_message(mcp):
    connect_mock = AsyncMock(side_effect=socket.gaierror(-2, "Name or service not known"))

    with (
        patch("app.tools.capture_realtime_ws.websockets.connect", connect_mock),
        pytest.raises(
            ToolError,
            match=r"Failed to resolve WebSocket host 'ws\.eodhistoricaldata\.com': Name or service not known\.",
        ),
    ):
        await _invoke_tool(
            mcp,
            "capture_realtime_ws",
            {
                "feed": "forex",
                "symbols": "EURUSD",
            },
        )


# ---------------------------------------------------------------------------
# 3. Error responses — API returns None or error dict
# ---------------------------------------------------------------------------

ERROR_RESPONSE_TOOLS = [
    ("get_exchanges_list", {}, "get_exchanges_list"),
    ("get_historical_stock_prices", {"ticker": "AAPL.US"}, "get_historical_stock_prices"),
    ("get_live_price_data", {"ticker": "AAPL.US"}, "get_live_price_data"),
    ("get_company_news", {"ticker": "AAPL.US"}, "get_company_news"),
    ("get_user_details", {}, "get_user_details"),
    ("get_upcoming_earnings", {}, "get_upcoming_earnings"),
    ("get_bulk_fundamentals", {"exchange": "US"}, "get_bulk_fundamentals"),
    ("stock_screener", {}, "get_stock_screener_data"),
    ("get_macro_indicator", {"country": "USA"}, "get_macro_indicator"),
    ("get_sentiment_data", {"symbols": "AAPL.US"}, "get_sentiment_data"),
    # Expanded coverage for error-path auto (TST-10)
    ("get_exchange_tickers", {"exchange_code": "US"}, "get_exchange_tickers"),
    ("get_stocks_from_search", {"query": "apple"}, "get_stocks_from_search"),
    ("get_upcoming_dividends", {"symbol": "AAPL.US"}, "get_upcoming_dividends"),
    ("get_exchange_details", {"exchange_code": "US"}, "get_exchange_details"),
    ("get_historical_market_cap", {"ticker": "AAPL.US"}, "get_historical_market_cap"),
    ("get_historical_dividends", {"ticker": "AAPL.US"}, "get_historical_dividends"),
    ("get_historical_splits", {"ticker": "AAPL.US"}, "get_historical_splits"),
    ("get_insider_transactions", {"symbol": "AAPL.US"}, "get_insider_transactions"),
    ("get_technical_indicators", {"ticker": "AAPL.US", "function": "sma"}, "get_technical_indicators"),
    ("get_news_word_weights", {"ticker": "AAPL.US"}, "get_news_word_weights"),
    ("get_stock_market_logos", {"symbol": "AAPL.US"}, "get_stock_market_logos"),
    ("get_us_live_extended_quotes", {"symbols": "AAPL.US"}, "get_us_live_extended_quotes"),
    ("get_symbol_change_history", {}, "get_symbol_change_history"),
    ("get_earnings_trends", {"symbols": "AAPL.US"}, "get_earnings_trends"),
    ("get_economic_events", {}, "get_economic_events"),
    ("resolve_ticker", {"query": "apple"}, "resolve_ticker"),
    ("get_cboe_indices_list", {}, "get_cboe_indices_list"),
    ("get_real_estate_countries", {}, "get_real_estate_countries"),
    ("get_real_estate_selected_prices", {"code": "US"}, "get_real_estate_selected_prices"),
    ("get_real_estate_detailed_prices", {"code": "US"}, "get_real_estate_detailed_prices"),
    ("get_real_estate_detailed_series", {"code": "US"}, "get_real_estate_detailed_series"),
    ("mp_indices_list", {}, "get_mp_indices_list"),
    ("get_mp_investverte_esg_list_companies", {}, "get_mp_investverte_esg_list_companies"),
    ("get_mp_investverte_esg_view_company", {"symbol": "AAPL"}, "get_mp_investverte_esg_view_company"),
    # More tools for broader error-path coverage
    ("get_mp_investverte_esg_view_country", {"symbol": "US"}, "get_mp_investverte_esg_view_country"),
    ("get_mp_investverte_esg_view_sector", {"symbol": "Airlines"}, "get_mp_investverte_esg_view_sector"),
    ("get_mp_investverte_esg_list_countries", {}, "get_mp_investverte_esg_list_countries"),
    ("get_mp_investverte_esg_list_sectors", {}, "get_mp_investverte_esg_list_sectors"),
    ("get_stock_market_logos_svg", {"symbol": "AAPL.US"}, "get_stock_market_logos_svg"),
    ("get_mp_tradinghours_list_markets", {}, "get_mp_tradinghours_list_markets"),
    ("get_mp_tradinghours_market_details", {"fin_id": "us.nyse"}, "get_mp_tradinghours_market_details"),
    ("get_mp_tradinghours_market_status", {"fin_id": "us.nyse"}, "get_mp_tradinghours_market_status"),
    ("get_mp_tradinghours_lookup_markets", {"q": "NYSE"}, "get_mp_tradinghours_lookup_markets"),
    ("get_us_options_underlyings", {}, "get_mp_us_options_underlyings"),
    ("get_upcoming_splits", {}, "get_upcoming_splits"),
    ("get_mp_praams_risk_scoring_by_ticker", {"ticker": "AAPL.US"}, "get_mp_praams_risk_scoring_by_ticker"),
    ("get_mp_praams_risk_scoring_by_isin", {"isin": "US0378331005"}, "get_mp_praams_risk_scoring_by_isin"),
    ("get_mp_praams_bank_balance_sheet_by_ticker", {"ticker": "AAPL.US"}, "get_mp_praams_bank_balance_sheet_by_ticker"),
    (
        "get_mp_praams_bank_income_statement_by_ticker",
        {"ticker": "AAPL.US"},
        "get_mp_praams_bank_income_statement_by_ticker",
    ),
    (
        "get_mp_praams_bond_analyze_by_isin",
        {"isin": "US0378331005"},
        "get_mp_praams_bond_analyze_by_isin",
    ),
    ("mp_index_components", {"symbol": "GSPC.INDX"}, "get_mp_index_components"),
    # Note: options tools (get_mp_us_options_*) don't check for error dicts — excluded
    (
        "get_mp_praams_bank_balance_sheet_by_isin",
        {"isin": "US0378331005"},
        "get_mp_praams_bank_balance_sheet_by_isin",
    ),
    (
        "get_mp_praams_bank_income_statement_by_isin",
        {"isin": "US0378331005"},
        "get_mp_praams_bank_income_statement_by_isin",
    ),
    # Credit & Sovereign Risk
    ("get_credit_sovereign_risk_premium", {"country": "USA"}, "get_credit_sovereign_risk_premium"),
    ("get_credit_sovereign_credit_ratings", {"country": "DEU"}, "get_credit_sovereign_credit_ratings"),
    ("get_credit_sovereign_cds_spreads", {"country": "ITA"}, "get_credit_sovereign_cds_spreads"),
    ("get_credit_sovereign_default_spreads", {"rating": "Baa2"}, "get_credit_sovereign_default_spreads"),
    ("get_credit_corporate_cmdi", {}, "get_credit_corporate_cmdi"),
    ("get_credit_corporate_hqm_yields", {"tenor": 10, "type": "spot"}, "get_credit_corporate_hqm_yields"),
    ("get_credit_cds_market_aggregates", {"metric": "gross_notional"}, "get_credit_cds_market_aggregates"),
    # Sanctions
    ("get_sanctions_entities", {"source": "ofac"}, "get_sanctions_entities"),
    ("get_sanctions_vessels", {"source": "ofac"}, "get_sanctions_vessels"),
    ("get_sanctions_programs", {}, "get_sanctions_programs"),
    ("get_sanctions_sources", {}, "get_sanctions_sources"),
    # Interest Rates
    ("get_rates_reference_rates", {"code": "SOFR"}, "get_rates_reference_rates"),
    ("get_rates_policy_rates", {"central_bank": "FED"}, "get_rates_policy_rates"),
    ("get_rates_funding_stress", {"code": "EFFR_SOFR"}, "get_rates_funding_stress"),
]


# resolve_ticker handles None as "no results" rather than an error
_NULL_EXCLUDES = {"resolve_ticker"}
_NULL_RESPONSE_TOOLS = [c for c in ERROR_RESPONSE_TOOLS if c[0] not in _NULL_EXCLUDES]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name,args,mock_module",
    _NULL_RESPONSE_TOOLS,
    ids=[c[0] for c in _NULL_RESPONSE_TOOLS],
)
async def test_null_response_raises(mcp, tool_name, args, mock_module):
    """Tool raises ToolError when API returns None."""
    with pytest.raises(ToolError):
        target = _mock_path(mock_module)
        with patch(target, new_callable=AsyncMock, return_value=None):
            await _invoke_tool(mcp, tool_name, args)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name,args,mock_module",
    ERROR_RESPONSE_TOOLS,
    ids=[c[0] for c in ERROR_RESPONSE_TOOLS],
)
async def test_error_response_raises(mcp, tool_name, args, mock_module):
    """Tool raises ToolError when API returns an error dict."""
    target = _mock_path(mock_module)
    with (
        pytest.raises(ToolError, match="Forbidden"),
        patch(target, new_callable=AsyncMock, return_value={"error": "Forbidden"}),
    ):
        await _invoke_tool(mcp, tool_name, args)


# ---------------------------------------------------------------------------
# 4. Success responses — valid data returns JSON string
# ---------------------------------------------------------------------------

SUCCESS_TOOLS = [
    ("get_exchanges_list", {}, "get_exchanges_list", [{"Code": "US"}]),
    ("get_exchange_tickers", {"exchange_code": "US"}, "get_exchange_tickers", [{"Code": "AAPL"}]),
    ("get_historical_stock_prices", {"ticker": "AAPL.US"}, "get_historical_stock_prices", [{"close": 150}]),
    ("get_live_price_data", {"ticker": "AAPL.US"}, "get_live_price_data", {"close": 150}),
    ("get_user_details", {}, "get_user_details", {"name": "manual"}),
    ("get_upcoming_earnings", {}, "get_upcoming_earnings", {"earnings": []}),
    ("get_macro_indicator", {"country": "USA"}, "get_macro_indicator", [{"value": 1.5}]),
    ("get_sentiment_data", {"symbols": "AAPL.US"}, "get_sentiment_data", {"AAPL.US": []}),
    ("stock_screener", {}, "get_stock_screener_data", [{"ticker": "AAPL"}]),
    # Expanded success-path coverage
    ("get_exchange_details", {"exchange_code": "US"}, "get_exchange_details", {"Name": "US"}),
    ("get_upcoming_dividends", {"symbol": "AAPL.US"}, "get_upcoming_dividends", [{"symbol": "AAPL"}]),
    ("get_upcoming_splits", {}, "get_upcoming_splits", [{"code": "AAPL"}]),
    ("get_historical_dividends", {"ticker": "AAPL.US"}, "get_historical_dividends", [{"date": "2025-02-07"}]),
    ("get_historical_splits", {"ticker": "AAPL.US"}, "get_historical_splits", [{"date": "2020-08-31"}]),
    ("get_insider_transactions", {"symbol": "AAPL.US"}, "get_insider_transactions", [{"shares": 1000}]),
    ("get_symbol_change_history", {}, "get_symbol_change_history", [{"old_code": "FB"}]),
    ("get_cboe_indices_list", {}, "get_cboe_indices_list", [{"code": "BDE30P"}]),
    ("get_real_estate_countries", {}, "get_real_estate_countries", {"data": [{"code": "US"}]}),
    (
        "get_real_estate_detailed_series",
        {"code": "US"},
        "get_real_estate_detailed_series",
        {"data": [{"title": "Whole country"}], "meta": {"country_code": "US", "total": 1}},
    ),
    ("mp_indices_list", {}, "get_mp_indices_list", [{"symbol": "GSPC"}]),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name,args,mock_module,mock_data",
    SUCCESS_TOOLS,
    ids=[c[0] for c in SUCCESS_TOOLS],
)
async def test_success_returns_json(mcp, tool_name, args, mock_module, mock_data):
    """Tool returns valid JSON string on successful API response."""
    text, _ = await _call(mcp, tool_name, args, mock_module, mock_return=mock_data)
    parsed = json.loads(text)
    assert parsed == mock_data


# ---------------------------------------------------------------------------
# 5. get_fundamentals_data — multi-request tool (dedicated auto)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fundamentals_url_and_general_call(mcp):
    """get_fundamentals_data hits /fundamentals/<ticker> with filter=General first."""
    general_resp = {"Type": "Common Stock", "Code": "AAPL", "Exchange": "US"}
    sections_resp = {"Highlights": {"MarketCap": 3e12}}

    call_count = 0

    async def _side_effect(url, *a, **kw):
        nonlocal call_count
        call_count += 1
        url_str = str(url)
        if "filter=General" in url_str:
            return general_resp
        # All subsequent calls (sections, financials) return empty dict
        return sections_resp

    target = _mock_path("get_fundamentals_data")
    with patch(target, side_effect=_side_effect):
        result = await _invoke_tool(mcp, "get_fundamentals_data", {"ticker": "AAPL.US"})
    # _call_tool returns list[EmbeddedResource] directly
    content = result[0]
    text = content.resource.text if hasattr(content, "resource") else content.text
    parsed = json.loads(text)
    assert parsed["General"]["Type"] == "Common Stock"
    assert call_count >= 2  # at least General + sections


# ---------------------------------------------------------------------------
# 6. Sanitization — invisible chars, recursive stripping, news HTML/truncation
# ---------------------------------------------------------------------------


class TestStripInvisibleChars:
    def test_removes_zero_width_chars(self):
        from app.response_formatter import _strip_invisible_chars

        text = "hello\u200bworld\u200ctest\ufeff"
        assert _strip_invisible_chars(text) == "helloworldtest"

    def test_preserves_normal_text(self):
        from app.response_formatter import _strip_invisible_chars

        text = "Hello, World! 123 àéîöü"
        assert _strip_invisible_chars(text) == text

    def test_removes_rtl_ltr_overrides(self):
        from app.response_formatter import _strip_invisible_chars

        text = "price\u202eis\u202d100"
        assert _strip_invisible_chars(text) == "priceis100"


class TestSanitizeData:
    def test_recursive_dict_and_list(self):
        from app.response_formatter import _sanitize_data

        data = {
            "name": "manual\u200b",
            "items": ["\u200bhidden", {"nested": "val\ufeff"}],
            "count": 42,
        }
        result = _sanitize_data(data)
        assert result == {
            "name": "manual",
            "items": ["hidden", {"nested": "val"}],
            "count": 42,
        }

    def test_passthrough_non_string(self):
        from app.response_formatter import _sanitize_data

        assert _sanitize_data(42) == 42
        assert _sanitize_data(None) is None
        assert _sanitize_data(3.14) == 3.14


class TestNewsArticleSanitization:
    @pytest.mark.asyncio
    async def test_html_is_stripped_without_truncation(self, mcp):
        """Tool strips HTML from title/content while preserving full text length."""
        articles = [
            {
                "title": "<b>Breaking</b> News",
                "content": "<p>" + ("A" * 6000) + "</p>",
                "link": "https://example.com",
            }
        ]
        text, _ = await _call(
            mcp,
            "get_company_news",
            {"ticker": "AAPL.US"},
            "get_company_news",
            mock_return=articles,
        )
        parsed = json.loads(text)
        article = parsed[0]
        assert article["title"] == "Breaking News"
        assert article["content"] == "A" * 6000
