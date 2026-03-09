# get_fundamentals_data.py

import datetime as dt
import json
from typing import Any

from app.api_client import make_request
from app.config import EODHD_API_BASE
from app.validators import validate_ticker
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

# --------------------------------
# Utilities & small helpers
# --------------------------------


def _to_date(s: str | None) -> dt.date | None:
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s)
    except Exception:
        return None


def _in_range(date_str: str, start: dt.date | None, end: dt.date | None) -> bool:
    """
    Inclusive date range check. Accepts YYYY-MM-DD.
    If start or end is None -> unbounded on that side.
    Returns False when the string cannot be parsed as a date.
    """
    try:
        d = dt.date.fromisoformat(date_str)
    except Exception:
        return False
    if start and d < start:
        return False
    if end and d > end:
        return False
    return True


def _build_url(ticker: str, params: dict[str, Any]) -> str:
    base = f"{EODHD_API_BASE}/fundamentals/{ticker}?fmt=json"
    parts: list[str] = []
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, bool):
            parts.append(f"{k}={'1' if v else '0'}")
        else:
            parts.append(f"{k}={v}")
    if parts:
        return base + "&" + "&".join(parts)
    return base


def _merge_tree(dest: dict[str, Any], src: dict[str, Any]) -> None:
    """Shallow-merge top-level dicts (right wins on conflicts)."""
    for k, v in src.items():
        dest[k] = v


def _token_override(api_token: str | None, api_key: str | None) -> str | None:
    """
    Accept api_token (preferred) and api_key (alias) as per-call overrides.
    """
    t = (api_token or "").strip() if isinstance(api_token, str) else ""
    if t:
        return t
    k = (api_key or "").strip() if isinstance(api_key, str) else ""
    return k or None


# --------------------------------
# Fetchers
# --------------------------------


async def _fetch_filtered_block(
    ticker: str,
    api_token: str | None,
    filter_expr: str,
    extra_params: dict[str, Any] | None = None,
) -> Any:
    params: dict[str, Any] = {"filter": filter_expr}
    if api_token:
        params["api_token"] = api_token
    if extra_params:
        for k, v in extra_params.items():
            params[k] = v
    url = _build_url(ticker, params)
    data = await make_request(url)
    return data


async def _fetch_general(ticker: str, api_token: str | None) -> dict[str, Any]:
    url = _build_url(ticker, {"filter": "General", "api_token": api_token} if api_token else {"filter": "General"})
    data = await make_request(url)
    if not isinstance(data, dict) or "Type" not in data:
        raise RuntimeError("Unexpected 'General' response: missing 'Type'")
    return data


async def _fetch_sections_bulk(
    ticker: str,
    api_token: str | None,
    sections: list[str],
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Request multiple top-level sections with comma-separated filter.
    Returns a dict (top-level keys = requested sections).
    """
    if not sections:
        return {}
    joined = ",".join(sections)
    data = await _fetch_filtered_block(ticker, api_token, joined, extra_params=extra_params)
    if isinstance(data, dict):
        return data
    # If a single section came back as a direct block, wrap it to keep the shape predictable.
    return {sections[0]: data}


async def _discover_financial_dates_from_outstanding_shares(
    ticker: str,
    api_token: str | None,
    start: dt.date | None,
    end: dt.date | None,
) -> tuple[list[str], list[str], dict[str, Any]]:
    """
    Returns (quarterly_dates, annual_dates, full_outstandingShares_block)
    The dates returned are taken from 'dateFormatted' and filtered by [start, end].
    """
    os_block = await _fetch_filtered_block(ticker, api_token, "outstandingShares")
    q_dates: list[str] = []
    a_dates: list[str] = []

    if isinstance(os_block, dict):
        for kind in ("quarterly", "annual"):
            sub = os_block.get(kind)
            if isinstance(sub, dict):
                # API uses numeric-string keys ("0","1"...). Sort by key to preserve order.
                for _, node in sorted(sub.items(), key=lambda kv: kv[0]):
                    if not isinstance(node, dict):
                        continue
                    df = str(node.get("dateFormatted") or "").strip()
                    if df and _in_range(df, start, end):
                        if kind == "quarterly":
                            q_dates.append(df)
                        else:
                            a_dates.append(df)

    return q_dates, a_dates, os_block if isinstance(os_block, dict) else {}


async def _fetch_financials_for_dates(
    ticker: str,
    api_token: str | None,
    quarter_dates: list[str],
    annual_dates: list[str],
) -> dict[str, Any]:
    """
    Fetch leaves for Financials statements on the specific dates discovered via outstandingShares.
    """
    result: dict[str, Any] = {
        "Financials": {
            "Balance_Sheet": {"quarterly": {}, "yearly": {}},
            "Cash_Flow": {"quarterly": {}, "yearly": {}},
            "Income_Statement": {"quarterly": {}, "yearly": {}},
        }
    }
    statements = ("Balance_Sheet", "Cash_Flow", "Income_Statement")

    # Quarterlies
    for d in quarter_dates:
        for stmt in statements:
            path = f"Financials::{stmt}::quarterly::{d}"
            payload = await _fetch_filtered_block(ticker, api_token, path)
            result["Financials"][stmt]["quarterly"][d] = payload

    # Annuals
    for d in annual_dates:
        for stmt in statements:
            path = f"Financials::{stmt}::yearly::{d}"
            payload = await _fetch_filtered_block(ticker, api_token, path)
            result["Financials"][stmt]["yearly"][d] = payload

    return result


def _prune_common_stock_by_date(
    assembled: dict[str, Any],
    start: dt.date | None,
    end: dt.date | None,
) -> dict[str, Any]:
    """
    Applies pruning rules:
    1) outstandingShares annual/quarterly — remove nodes with dateFormatted outside [from, to]
    2) Earnings: History / Trend / Annual — remove keys (dates) outside [from, to]
    3) Financials::<statement>::(quarterly|yearly) — remove report nodes (date keys) outside [from, to]
    """
    if not start and not end:
        return assembled

    # 1) outstandingShares
    os_block = assembled.get("outstandingShares")
    if isinstance(os_block, dict):
        for freq in ("annual", "quarterly"):
            sub = os_block.get(freq)
            if isinstance(sub, dict):
                to_del = []
                for k, v in sub.items():
                    if not isinstance(v, dict):
                        to_del.append(k)
                        continue
                    df = str(v.get("dateFormatted") or "").strip()
                    if not df or not _in_range(df, start, end):
                        to_del.append(k)
                for k in to_del:
                    sub.pop(k, None)

    # 2) Earnings maps
    earnings = assembled.get("Earnings")
    if isinstance(earnings, dict):
        for subkey in ("History", "Trend", "Annual"):
            sub = earnings.get(subkey)
            if isinstance(sub, dict):
                to_del = [k for k in list(sub.keys()) if not _in_range(k, start, end)]
                for k in to_del:
                    sub.pop(k, None)

    # 3) Financials
    fin = assembled.get("Financials")
    if isinstance(fin, dict):
        for stmt in ("Balance_Sheet", "Cash_Flow", "Income_Statement"):
            stmt_block = fin.get(stmt)
            if isinstance(stmt_block, dict):
                for period in ("quarterly", "yearly"):
                    period_block = stmt_block.get(period)
                    if isinstance(period_block, dict):
                        to_del = [k for k in list(period_block.keys()) if not _in_range(k, start, end)]
                        for k in to_del:
                            period_block.pop(k, None)

    return assembled


def _default_sections_for_type(asset_type: str) -> list[str]:
    t = asset_type.strip().lower()
    if t == "common stock":
        return [
            "General",
            "Highlights",
            "Valuation",
            "SharesStats",
            "Technicals",
            "SplitsDividends",
            "AnalystRatings",
            "Holders",
            "InsiderTransactions",
            "outstandingShares",
            "Earnings",
            # Financials handled separately (can be very large)
        ]
    if t == "etf":
        return ["General", "Technicals", "ETF_Data"]
    if t == "fund":
        return ["General", "MutualFund_Data"]
    if t == "index":
        return ["General"]  # Components/Historical controlled via extra_params
    if t == "crypto":
        return ["General", "Tech", "Resources", "Statistics"]
    return ["General"]


# --------------------------------
# MCP Tool
# --------------------------------


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_fundamentals_data(
        ticker: str,  # "AAPL.US", "VTI.US", "SWPPX.US", "GSPC.INDX", etc.
        api_token: str | None = None,  # per-call override (preferred name)
        api_key: str | None = None,  # per-call override (alias)
        # Common Stock date pruning window (inclusive). For Indices, pass 'from'/'to' via extra_params.
        from_date: str | None = None,  # "YYYY-MM-DD"
        to_date: str | None = None,  # "YYYY-MM-DD"
        # Explicit sections (top-level) to fetch; if omitted, defaults by detected Type.
        sections: list[str] | None = None,  # e.g. ["General","Highlights","Earnings"]
        # For indices or extra flags: {"historical": 1, "from": "2020-01-01", "to": "2023-01-01"}
        extra_params: dict[str, Any] | None = None,
        # For Common Stock, whether to include Financials. When a date window is provided,
        # the tool only fetches leaves for in-range dates discovered via outstandingShares.
        include_financials: bool = True,
        # Keep parity with your other tools
        fmt: str = "json",
    ) -> str:
        """

        Retrieve fundamental data for a single stock, ETF, mutual fund, index, or crypto.
        Auto-detects asset type. For stocks: returns financials (income statement, balance sheet, cash flow),
        earnings, valuation, analyst ratings, holders, insider transactions, and outstanding shares.
        For ETFs: returns holdings, asset allocation, sector/country weights. For mutual funds: fund-specific data.
        Supports date-range pruning to limit financials and earnings to a specific window.
        For bulk fundamentals across many tickers at once, use get_bulk_fundamentals instead.
        For price data, use get_historical_stock_prices or get_live_price_data instead.

        - ticker: If you only have a company name or ISIN, call resolve_ticker first.

        Returns:
            Nested object; structure depends on asset Type:

            Common Stock — top-level keys:
            - General: name, exchange, currency, sector, industry, description, etc.
            - Highlights: marketCap, EBITDA, PE, EPS, dividendYield, etc.
            - Valuation: trailing/forward PE, PEG, price-to-sales/book, EV ratios
            - SharesStats: shares outstanding, float, percent insiders/institutions
            - Technicals: beta, 52wHigh/Low, moving averages, short ratio
            - SplitsDividends: forward/trailing dividend rate & yield, payout ratio, split history
            - AnalystRatings: target price, strong buy/buy/hold/sell/strong sell counts
            - Holders: top institutional & fund holders with shares/weight
            - InsiderTransactions: array of insider trades (date, name, shares, value)
            - outstandingShares: quarterly & annual share counts by date
            - Earnings: History (actual/estimate EPS), Trend, Annual
            - Financials: Balance_Sheet, Cash_Flow, Income_Statement (quarterly & yearly)

            ETF — top-level keys:
            - General, Technicals
            - ETF_Data: Holdings (top N positions), Sector_Weights, World_Regions,
              Top_10_Holdings, Asset_Allocation, performance, fees

            Mutual Fund — top-level keys:
            - General
            - MutualFund_Data: fund family, category, NAV, yield, holdings, sector weights

            Index — General only (pass extra_params={'historical': 1} for components).

        Examples:
            "Apple fundamentals" → ticker="AAPL.US"
            "Tesla earnings and valuation for 2025" → ticker="TSLA.US", sections=["Earnings", "Valuation"], from_date="2025-01-01", to_date="2025-12-31"
            "Vanguard Total Stock Market ETF info" → ticker="VTI.US", sections=["General", "ETF_Data"]


        """
        # --- Validate basics
        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        ticker = validate_ticker(ticker)

        token = _token_override(api_token, api_key)
        start = _to_date(from_date)
        end = _to_date(to_date)
        if to_date and from_date and start and end and end < start:
            raise ToolError("'to_date' must be >= 'from_date'.")

        # --- 1) Detect Type (via General)
        try:
            general = await _fetch_general(ticker, token)
        except Exception as e:
            raise ToolError(f"Failed to get General: {e}")

        asset_type = str(general.get("Type") or "").strip()
        if not asset_type:
            raise ToolError("Unable to determine asset Type from General section.")

        # --- 2) Decide sections to pull (excluding 'General' which we already have)
        chosen_sections = sections if sections else _default_sections_for_type(asset_type)
        non_general_sections = [s for s in chosen_sections if s != "General"]

        assembled: dict[str, Any] = {"General": general}

        # --- 3) Fetch non-Financials in bulk where possible
        non_financial_sections: list[str] = []
        try:
            # We never ask for 'Financials' in the bulk; we fetch that separately below.
            for s in non_general_sections:
                if str(s).strip().lower() != "financials":
                    non_financial_sections.append(str(s))
            if non_financial_sections:
                bulk = await _fetch_sections_bulk(
                    ticker,
                    token,
                    non_financial_sections,
                    extra_params=extra_params if isinstance(extra_params, dict) else None,
                )
                _merge_tree(assembled, bulk)
        except Exception as e:
            raise ToolError("Failed to fetch sections " + repr(non_financial_sections) + ": " + repr(e))

        # --- 4) Financials handling for Common Stock
        if asset_type.lower() == "common stock" and include_financials:
            try:
                if start or end:
                    # Discover in-range dates via outstandingShares, then fetch leaves only for those dates
                    q_dates, a_dates, os_block = await _discover_financial_dates_from_outstanding_shares(
                        ticker, token, start, end
                    )
                    if os_block:
                        assembled["outstandingShares"] = os_block  # ensure we have this block for pruning
                    fin_tree = await _fetch_financials_for_dates(
                        ticker, token, quarter_dates=q_dates, annual_dates=a_dates
                    )
                    _merge_tree(assembled, fin_tree)
                else:
                    # No date window -> download full maps (quarterly & yearly) for each statement
                    fin_full: dict[str, Any] = {"Financials": {}}
                    for stmt in ("Balance_Sheet", "Cash_Flow", "Income_Statement"):
                        fin_full["Financials"].setdefault(stmt, {})
                        for period in ("quarterly", "yearly"):
                            path = f"Financials::{stmt}::{period}"
                            block = await _fetch_filtered_block(ticker, token, path)
                            fin_full["Financials"][stmt][period] = block
                    _merge_tree(assembled, fin_full)
            except Exception as e:
                raise ToolError(f"Failed to fetch Financials: {e}")

        # --- 5) Apply pruning if Common Stock and a date window was provided
        if asset_type.lower() == "common stock" and (start or end):
            assembled = _prune_common_stock_by_date(assembled, start, end)

        # --- 6) Return full JSON (do not reduce)
        try:
            return json.dumps(assembled, indent=2)
        except Exception:
            raise ToolError("Unexpected response format from API.")
