"""Parametrized tests for all 74 tool files.

Covers:
  1. URL construction — mock make_request, verify URL path + query params
  2. Input validation — invalid inputs raise ToolError
  3. Error responses — None / {error: ...} from API handled correctly
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from app.tools import register_all

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

API_SUCCESS = {"ok": True}


@pytest.fixture(scope="module")
def mcp():
    """Register all tools once for the module."""
    server = FastMCP("test")
    register_all(server)
    return server


def _mock_path(module_name: str) -> str:
    """Return the mock target for make_request in a tool module."""
    return f"app.tools.{module_name}.make_request"


async def _call(mcp, tool_name, args, mock_module, mock_return=None):
    """Call a tool with mocked make_request, return (result_text, mock)."""
    target = _mock_path(mock_module)
    mock = AsyncMock(return_value=mock_return if mock_return is not None else API_SUCCESS)
    with patch(target, mock):
        result = await mcp.call_tool(tool_name, args)
    text = result.content[0].text
    return text, mock


# ---------------------------------------------------------------------------
# 1. URL construction — valid inputs → correct API URL
# ---------------------------------------------------------------------------

# (tool_name, args, mock_module, expected_url_fragments)
URL_CASES = [
    # Core endpoints
    ("get_exchanges_list", {}, "get_exchanges_list", ["/exchanges-list/", "fmt=json"]),
    ("get_exchange_tickers", {"exchange_code": "US"}, "get_exchange_tickers", ["/exchange-symbol-list/US", "fmt=json"]),
    ("get_historical_stock_prices", {"ticker": "AAPL.US"}, "get_historical_stock_prices", ["/eod/AAPL.US", "period=d", "fmt=json"]),
    ("get_historical_stock_prices", {"ticker": "AAPL.US", "period": "m", "order": "d"}, "get_historical_stock_prices", ["/eod/AAPL.US", "period=m", "order=d"]),
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
    ("get_historical_market_cap", {"ticker": "AAPL.US"}, "get_historical_market_cap", ["/historical-market-cap/AAPL.US"]),
    ("get_insider_transactions", {"symbol": "AAPL.US"}, "get_insider_transactions", ["/insider-transactions"]),
    # Technical
    ("get_technical_indicators", {"ticker": "AAPL.US", "function": "sma"}, "get_technical_indicators", ["/technical/AAPL.US", "function=sma"]),
    # News
    ("get_news_word_weights", {"ticker": "AAPL.US"}, "get_news_word_weights", ["/news", "s=AAPL.US"]),
    # Logos
    ("get_stock_market_logos", {"symbol": "AAPL.US"}, "get_stock_market_logos", ["/logo/AAPL.US"]),
    ("get_stock_market_logos_svg", {"symbol": "AAPL.US"}, "get_stock_market_logos_svg", ["/logo-svg/AAPL.US"]),
    # US market
    ("get_us_live_extended_quotes", {"symbols": "AAPL.US"}, "get_us_live_extended_quotes", ["/us-quote-delayed"]),
    ("get_us_tick_data", {"ticker": "AAPL.US", "from_timestamp": 1694455200, "to_timestamp": 1694541600}, "get_us_tick_data", ["/ticks/", "s=AAPL.US"]),
    # CBOE
    ("get_cboe_index_data", {"index_code": "BDE30P", "feed_type": "snapshot_official_closing", "date": "2017-02-01"}, "get_cboe_index_data", ["/cboe/index"]),
    ("get_cboe_indices_list", {}, "get_cboe_indices_list", ["/cboe/"]),
    # Treasury
    ("get_ust_bill_rates", {}, "get_ust_bill_rates", ["/ust/bill-rates"]),
    ("get_ust_long_term_rates", {}, "get_ust_long_term_rates", ["/ust/long-term-rates"]),
    ("get_ust_real_yield_rates", {}, "get_ust_real_yield_rates", ["/ust/real-yield-rates"]),
    ("get_ust_yield_rates", {}, "get_ust_yield_rates", ["/ust/yield-rates"]),
    # Intraday
    ("get_intraday_historical_data", {"ticker": "AAPL.US"}, "get_intraday_historical_data", ["/intraday/AAPL.US"]),
    # Marketplace — illio (market insights use param "id", not "index")
    ("get_mp_illio_market_insights_best_worst", {"id": "SnP500"}, "get_mp_illio_market_insights_best_worst", ["/mp/illio/chapters/best-and-worst/"]),
    ("get_mp_illio_market_insights_performance", {"id": "SnP500"}, "get_mp_illio_market_insights_performance", ["/mp/illio/chapters/performance/"]),
    ("get_mp_illio_market_insights_risk_return", {"id": "SnP500"}, "get_mp_illio_market_insights_risk_return", ["/mp/illio/chapters/risk/"]),
    ("get_mp_illio_market_insights_volatility", {"id": "SnP500"}, "get_mp_illio_market_insights_volatility", ["/mp/illio/chapters/volatility/"]),
    ("get_mp_illio_market_insights_beta_bands", {"id": "SnP500"}, "get_mp_illio_market_insights_beta_bands", ["/mp/illio/chapters/beta-bands/"]),
    ("get_mp_illio_market_insights_largest_volatility", {"id": "SnP500"}, "get_mp_illio_market_insights_largest_volatility", ["/mp/illio/chapters/volume/"]),
    ("mp_illio_performance_insights", {"id": "SnP500"}, "get_mp_illio_performance_insights", ["/mp/illio/categories/performance/"]),
    ("mp_illio_risk_insights", {"id": "SnP500"}, "get_mp_illio_risk_insights", ["/mp/illio/categories/risk/"]),
    # Marketplace — indices
    ("mp_index_components", {"symbol": "GSPC.INDX"}, "get_mp_index_components", ["/mp/unicornbay/spglobal/comp/"]),
    ("mp_indices_list", {}, "get_mp_indices_list", ["/mp/unicornbay/spglobal/list"]),
    # Marketplace — ESG
    ("get_mp_investverte_esg_list_companies", {}, "get_mp_investverte_esg_list_companies", ["/mp/investverte/companies"]),
    ("get_mp_investverte_esg_list_countries", {}, "get_mp_investverte_esg_list_countries", ["/mp/investverte/countries"]),
    ("get_mp_investverte_esg_list_sectors", {}, "get_mp_investverte_esg_list_sectors", ["/mp/investverte/sectors"]),
    ("get_mp_investverte_esg_view_company", {"symbol": "AAPL"}, "get_mp_investverte_esg_view_company", ["/mp/investverte/esg/AAPL"]),
    ("get_mp_investverte_esg_view_country", {"symbol": "US"}, "get_mp_investverte_esg_view_country", ["/mp/investverte/country/US"]),
    ("get_mp_investverte_esg_view_sector", {"symbol": "Airlines"}, "get_mp_investverte_esg_view_sector", ["/mp/investverte/sector/Airlines"]),
    # Marketplace — PRAAMS
    ("get_mp_praams_bank_balance_sheet_by_isin", {"isin": "US0378331005"}, "get_mp_praams_bank_balance_sheet_by_isin", ["/mp/praams/bank/balance_sheet/isin/"]),
    ("get_mp_praams_bank_balance_sheet_by_ticker", {"ticker": "AAPL.US"}, "get_mp_praams_bank_balance_sheet_by_ticker", ["/mp/praams/bank/balance_sheet/ticker/"]),
    ("get_mp_praams_bank_income_statement_by_isin", {"isin": "US0378331005"}, "get_mp_praams_bank_income_statement_by_isin", ["/mp/praams/bank/income_statement/isin/"]),
    ("get_mp_praams_bank_income_statement_by_ticker", {"ticker": "AAPL.US"}, "get_mp_praams_bank_income_statement_by_ticker", ["/mp/praams/bank/income_statement/ticker/"]),
    ("get_mp_praams_bond_analyze_by_isin", {"isin": "US0378331005"}, "get_mp_praams_bond_analyze_by_isin", ["/mp/praams/analyse/bond/"]),
    ("get_mp_praams_report_bond_by_isin", {"isin": "US0378331005", "email": "test@test.com"}, "get_mp_praams_report_bond_by_isin", ["/mp/praams/reports/bond/"]),
    ("get_mp_praams_report_equity_by_isin", {"isin": "US0378331005", "email": "test@test.com"}, "get_mp_praams_report_equity_by_isin", ["/mp/praams/reports/equity/isin/"]),
    ("get_mp_praams_report_equity_by_ticker", {"ticker": "AAPL.US", "email": "test@test.com"}, "get_mp_praams_report_equity_by_ticker", ["/mp/praams/reports/equity/ticker/"]),
    ("get_mp_praams_risk_scoring_by_isin", {"isin": "US0378331005"}, "get_mp_praams_risk_scoring_by_isin", ["/mp/praams/analyse/equity/isin/"]),
    ("get_mp_praams_risk_scoring_by_ticker", {"ticker": "AAPL.US"}, "get_mp_praams_risk_scoring_by_ticker", ["/mp/praams/analyse/equity/ticker/"]),
    ("get_mp_praams_smart_screener_equity", {"countries": [1]}, "get_mp_praams_smart_investment_screener_equity", ["/mp/praams/explore/equity"]),
    ("get_mp_praams_smart_screener_bond", {"countries": [1]}, "get_mp_praams_smart_investment_screener_bond", ["/mp/praams/explore/bond"]),
    # Marketplace — tick data & options
    ("get_mp_tick_data", {"ticker": "AAPL.US"}, "get_mp_tick_data", ["/mp/unicornbay/tickdata/ticks", "s=AAPL.US"]),
    ("get_us_options_contracts", {}, "get_mp_us_options_contracts", ["/mp/unicornbay/options/contracts"]),
    ("get_us_options_eod", {}, "get_mp_us_options_eod", ["/mp/unicornbay/options/eod"]),
    ("get_us_options_underlyings", {}, "get_mp_us_options_underlyings", ["/mp/unicornbay/options/underlying-symbols"]),
    # Marketplace — trading hours
    ("get_mp_tradinghours_list_markets", {}, "get_mp_tradinghours_list_markets", ["/mp/tradinghours/markets"]),
    ("get_mp_tradinghours_lookup_markets", {"q": "NYSE"}, "get_mp_tradinghours_lookup_markets", ["/mp/tradinghours/markets/lookup"]),
    ("get_mp_tradinghours_market_details", {"fin_id": "us.nyse"}, "get_mp_tradinghours_market_details", ["/mp/tradinghours/markets/details"]),
    ("get_mp_tradinghours_market_status", {"fin_id": "us.nyse"}, "get_mp_tradinghours_market_status", ["/mp/tradinghours/markets/status"]),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name,args,mock_module,url_fragments", URL_CASES, ids=[c[0] for c in URL_CASES])
async def test_url_construction(mcp, tool_name, args, mock_module, url_fragments):
    """Tool builds correct URL with expected path and query params."""
    text, mock = await _call(mcp, tool_name, args, mock_module)
    assert mock.call_count >= 1
    url = str(mock.call_args_list[0].args[0])
    for frag in url_fragments:
        assert frag in url, f"Expected '{frag}' in URL: {url}"


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
    ("get_technical_indicators", {"ticker": "", "function": "sma"}, "required"),
    # Exchange validation
    ("get_exchange_tickers", {"exchange_code": ""}, "required"),
    ("get_bulk_fundamentals", {"exchange": ""}, "required"),
    # Format validation
    ("get_exchanges_list", {"fmt": "xml"}, "json"),
    ("get_historical_stock_prices", {"ticker": "AAPL.US", "fmt": "xml"}, None),
    # Period/order validation
    ("get_historical_stock_prices", {"ticker": "AAPL.US", "period": "x"}, None),
    ("get_historical_stock_prices", {"ticker": "AAPL.US", "order": "x"}, None),
    # Technical indicators — function required
    ("get_technical_indicators", {"ticker": "AAPL.US", "function": "invalid_fn"}, None),
    # Macro — country required
    ("get_macro_indicator", {"country": ""}, None),
    # Sentiment — symbols required
    ("get_sentiment_data", {"symbols": ""}, "required"),
    # Company news — needs ticker or tag
    ("get_company_news", {}, None),
    # Resolve ticker — query required
    ("resolve_ticker", {"query": ""}, None),
    # Bulk fundamentals — limit range
    ("get_bulk_fundamentals", {"exchange": "US", "limit": 0}, None),
    ("get_bulk_fundamentals", {"exchange": "US", "limit": 501}, None),
    # Intraday — interval validation
    ("get_intraday_historical_data", {"ticker": "AAPL.US", "interval": "2m"}, None),
    # Tick data — ticker required
    ("get_mp_tick_data", {"ticker": ""}, "required"),
    # Economic events — comparison validation
    ("get_economic_events", {"comparison": "invalid"}, None),
    # Options — type validation
    ("get_us_options_contracts", {"type": "invalid"}, None),
    # Live price — additional_symbols too many (>20)
    ("get_live_price_data", {"ticker": "AAPL.US", "additional_symbols": [f"T{i}.US" for i in range(21)]}, None),
    # WebSocket — invalid feed
    ("capture_realtime_ws", {"feed": "invalid_feed", "symbols": "AAPL"}, None),
    # Stock screener — limit range
    ("stock_screener", {"limit": 0}, None),
    ("stock_screener", {"limit": 101}, None),
    # CBOE — all 3 params required
    ("get_cboe_index_data", {"index_code": "", "feed_type": "x", "date": "2017-01-01"}, None),
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
        await mcp.call_tool(tool_name, bad_args)


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
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name,args,mock_module",
    ERROR_RESPONSE_TOOLS,
    ids=[c[0] for c in ERROR_RESPONSE_TOOLS],
)
async def test_null_response_raises(mcp, tool_name, args, mock_module):
    """Tool raises ToolError when API returns None."""
    with pytest.raises(ToolError):
        target = _mock_path(mock_module)
        with patch(target, new_callable=AsyncMock, return_value=None):
            await mcp.call_tool(tool_name, args)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name,args,mock_module",
    ERROR_RESPONSE_TOOLS,
    ids=[c[0] for c in ERROR_RESPONSE_TOOLS],
)
async def test_error_response_raises(mcp, tool_name, args, mock_module):
    """Tool raises ToolError when API returns error dict."""
    with pytest.raises(ToolError):
        target = _mock_path(mock_module)
        with patch(target, new_callable=AsyncMock, return_value={"error": "Forbidden"}):
            await mcp.call_tool(tool_name, args)


# ---------------------------------------------------------------------------
# 4. Success responses — valid data returns JSON string
# ---------------------------------------------------------------------------

SUCCESS_TOOLS = [
    ("get_exchanges_list", {}, "get_exchanges_list", [{"Code": "US"}]),
    ("get_exchange_tickers", {"exchange_code": "US"}, "get_exchange_tickers", [{"Code": "AAPL"}]),
    ("get_historical_stock_prices", {"ticker": "AAPL.US"}, "get_historical_stock_prices", [{"close": 150}]),
    ("get_live_price_data", {"ticker": "AAPL.US"}, "get_live_price_data", {"close": 150}),
    ("get_user_details", {}, "get_user_details", {"name": "test"}),
    ("get_upcoming_earnings", {}, "get_upcoming_earnings", {"earnings": []}),
    ("get_macro_indicator", {"country": "USA"}, "get_macro_indicator", [{"value": 1.5}]),
    ("get_sentiment_data", {"symbols": "AAPL.US"}, "get_sentiment_data", {"AAPL.US": []}),
    ("stock_screener", {}, "get_stock_screener_data", [{"ticker": "AAPL"}]),
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
# 5. get_fundamentals_data — multi-request tool (dedicated tests)
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
        result = await mcp.call_tool("get_fundamentals_data", {"ticker": "AAPL.US"})
    text = result.content[0].text
    parsed = json.loads(text)
    assert parsed["General"]["Type"] == "Common Stock"
    assert call_count >= 2  # at least General + sections
