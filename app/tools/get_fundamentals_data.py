#get_fundamentals_data.py

import json
import datetime as dt
from typing import Any, Dict, List, Optional, Tuple, Union

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


# --------------------------------
# Utilities & small helpers
# --------------------------------

def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)

def _to_date(s: Optional[str]) -> Optional[dt.date]:
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s)
    except Exception:
        return None

def _in_range(date_str: str, start: Optional[dt.date], end: Optional[dt.date]) -> bool:
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

def _build_url(ticker: str, params: Dict[str, Union[str, int, float, bool]]) -> str:
    base = f"{EODHD_API_BASE}/fundamentals/{ticker}?fmt=json"
    parts: List[str] = []
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

def _merge_tree(dest: Dict[str, Any], src: Dict[str, Any]) -> None:
    """Shallow-merge top-level dicts (right wins on conflicts)."""
    for k, v in src.items():
        dest[k] = v


# --------------------------------
# Fetchers
# --------------------------------

async def _fetch_filtered_block(
    ticker: str,
    api_token: str,
    filter_expr: str,
    extra_params: Optional[Dict[str, Union[str, int, float, bool]]] = None,
) -> Any:
    params: Dict[str, Union[str, int, float, bool]] = {"api_token": api_token, "filter": filter_expr}
    if extra_params:
        for k, v in extra_params.items():
            params[k] = v
    url = _build_url(ticker, params)
    data = await make_request(url)
    return data

async def _fetch_general(ticker: str, api_token: str) -> Dict[str, Any]:
    url = _build_url(ticker, {"api_token": api_token, "filter": "General"})
    data = await make_request(url)
    if not isinstance(data, dict) or "Type" not in data:
        raise RuntimeError("Unexpected 'General' response: missing 'Type'")
    return data

async def _fetch_sections_bulk(
    ticker: str, api_token: str, sections: List[str], extra_params: Optional[Dict[str, Union[str, int, float, bool]]] = None
) -> Dict[str, Any]:
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
    api_token: str,
    start: Optional[dt.date],
    end: Optional[dt.date],
) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """
    Returns (quarterly_dates, annual_dates, full_outstandingShares_block)
    The dates returned are taken from 'dateFormatted' and filtered by [start, end].
    """
    os_block = await _fetch_filtered_block(ticker, api_token, "outstandingShares")
    q_dates: List[str] = []
    a_dates: List[str] = []

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
    api_token: str,
    quarter_dates: List[str],
    annual_dates: List[str],
) -> Dict[str, Any]:
    """
    Fetch leaves for Financials statements on the specific dates discovered via outstandingShares.
    """
    result: Dict[str, Any] = {
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
    assembled: Dict[str, Any], start: Optional[dt.date], end: Optional[dt.date]
) -> Dict[str, Any]:
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

def _default_sections_for_type(asset_type: str) -> List[str]:
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
        ticker: str,                                   # "AAPL.US", "VTI.US", "SWPPX.US", "GSPC.INDX", etc.
        api_token: Optional[str] = None,               # per-call override
        # Common Stock date pruning window (inclusive). For Indices, pass 'from'/'to' via extra_params.
        from_date: Optional[str] = None,               # "YYYY-MM-DD"
        to_date: Optional[str] = None,                 # "YYYY-MM-DD"
        # Explicit sections (top-level) to fetch; if omitted, defaults by detected Type.
        sections: Optional[list] = None,               # e.g. ["General","Highlights","Earnings"]
        # For indices or extra flags: {"historical": 1, "from": "2020-01-01", "to": "2023-01-01"}
        extra_params: Optional[dict] = None,
        # For Common Stock, whether to include Financials. When a date window is provided,
        # the tool only fetches leaves for in-range dates discovered via outstandingShares.
        include_financials: bool = True,
        # Keep parity with your other tools
        fmt: str = "json",
    ) -> str:
        """
        Get Fundamentals for Stocks, ETFs, Mutual Funds, and Indices.
        - Auto-detects asset Type via 'General'.
        - For Common Stock: if from/to are provided, prunes `outstandingShares`, `Earnings`, and `Financials`
          outside the window. Financials are fetched only for in-range period end dates (from outstandingShares).
        - For Indices: pass 'historical=1' and optional 'from'/'to' through `extra_params`.
        - Always returns JSON (fmt must be 'json').
        """
        # --- Validate basics
        if fmt != "json":
            return _err("Only 'json' is supported by this tool.")

        if not api_token:
            return _err("Parameter 'api_token' is required.")

        if not ticker or "." not in ticker:
            return _err("Parameter 'ticker' must be in 'SYMBOL.EXCHANGE' format (e.g., 'AAPL.US').")

        start = _to_date(from_date)
        end = _to_date(to_date)
        if to_date and from_date and start and end and end < start:
            return _err("'to_date' must be >= 'from_date'.")

        # --- 1) Detect Type (via General)
        try:
            general = await _fetch_general(ticker, api_token)
        except Exception as e:
            return _err(f"Failed to get General: {e}")

        asset_type = str(general.get("Type") or "").strip()
        if not asset_type:
            return _err("Unable to determine asset Type from General section.")

        # --- 2) Decide sections to pull (excluding 'General' which we already have)
        chosen_sections = sections if sections else _default_sections_for_type(asset_type)
        non_general_sections = [s for s in chosen_sections if s != "General"]

        assembled: Dict[str, Any] = {"General": general}

        # --- 3) Fetch non-Financials in bulk where possible
        try:
            # We never ask for 'Financials' in the bulk; we fetch that separately below.
            non_financial_sections = [s for s in non_general_sections if str(s).lower() != "financials"]
            if non_financial_sections:
                bulk = await _fetch_sections_bulk(
                    ticker,
                    api_token,
                    [str(s) for s in non_financial_sections],
                    extra_params=extra_params if isinstance(extra_params, dict) else None,
                )
                _merge_tree(assembled, bulk)
        except Exception as e:
            return _err(f"Failed to fetch sections {non_financial_sections}: {e}")

        # --- 4) Financials handling for Common Stock
        if asset_type.lower() == "common stock" and include_financials:
            try:
                if start or end:
                    # Discover in-range dates via outstandingShares, then fetch leaves only for those dates
                    q_dates, a_dates, os_block = await _discover_financial_dates_from_outstanding_shares(
                        ticker, api_token, start, end
                    )
                    if os_block:
                        assembled["outstandingShares"] = os_block  # ensure we have this block for pruning
                    fin_tree = await _fetch_financials_for_dates(
                        ticker, api_token, quarter_dates=q_dates, annual_dates=a_dates
                    )
                    _merge_tree(assembled, fin_tree)
                else:
                    # No date window -> download full maps (quarterly & yearly) for each statement
                    fin_full: Dict[str, Any] = {"Financials": {}}
                    for stmt in ("Balance_Sheet", "Cash_Flow", "Income_Statement"):
                        fin_full["Financials"].setdefault(stmt, {})
                        for period in ("quarterly", "yearly"):
                            path = f"Financials::{stmt}::{period}"
                            block = await _fetch_filtered_block(ticker, api_token, path)
                            fin_full["Financials"][stmt][period] = block
                    _merge_tree(assembled, fin_full)
            except Exception as e:
                return _err(f"Failed to fetch Financials: {e}")

        # --- 5) Apply pruning if Common Stock and a date window was provided
        if asset_type.lower() == "common stock" and (start or end):
            assembled = _prune_common_stock_by_date(assembled, start, end)

        # --- 6) Return full JSON (do not reduce)
        try:
            return json.dumps(assembled, indent=2)
        except Exception:
            return _err("Unexpected response format from API.")
