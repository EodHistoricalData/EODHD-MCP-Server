import json
import re
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

_RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources" / "references"

# ---------------------------------------------------------------------------
# Markdown → nested-dict parser
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")
_BOLD_KV_RE = re.compile(r"^\*\*(.+?)\*\*\s*:\s*(.*)")
_UL_RE = re.compile(r"^[-*]\s+(.*)")
_OL_RE = re.compile(r"^\d+\.\s+(.*)")
_TABLE_SEP_RE = re.compile(r"^\s*\|[\s\-:|]+\|\s*$")
_HR_RE = re.compile(r"^[-*_]{3,}\s*$")


def _strip_md(text: str) -> str:
    """Remove inline markdown formatting, keeping plain text."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # [link](url)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # **bold**
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text)  # *italic*
    text = re.sub(r"`(.+?)`", r"\1", text)  # `code`
    return text.strip()


def _put(sec: dict, key: str, val):
    """Insert *key* into *sec*, disambiguating duplicates."""
    if key not in sec:
        sec[key] = val
    else:
        c = 2
        while f"{key} ({c})" in sec:
            c += 1
        sec[f"{key} ({c})"] = val


def _parse_markdown(text: str) -> Any:
    """Parse a markdown document into a nested dict / list structure.

    Mapping rules
    -------------
    * ``# / ## / ###`` headings  → nested dict keys
    * ``**Key**: Value``         → key-value pair in current section
    * Markdown tables            → list of row-dicts
    * Bullet / numbered lists    → list of strings
    * Fenced code blocks         → string value (``example_<lang>``)
    * Block-quotes               → string value (``note``)
    * Plain text paragraphs      → string value (``text``)

    Leaf sections that contain only one anonymous block (table, list,
    text, or note) are "unwrapped" so the section value becomes the
    block itself rather than a single-key dict.
    """
    lines = text.split("\n")
    root: dict = {}
    stack: list[tuple[int, dict]] = [(0, root)]
    i, n = 0, len(lines)

    def cur() -> dict:
        return stack[-1][1]

    while i < n:
        s = lines[i].strip()

        # skip blanks and horizontal rules
        if not s or _HR_RE.match(s):
            i += 1
            continue

        # ── fenced code block ──────────────────────────────────────
        if s.startswith("```"):
            lang = s[3:].strip()
            buf: list[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            if i < n:
                i += 1
            key = f"example_{lang}" if lang else "example"
            _put(cur(), key, "\n".join(buf))
            continue

        # ── heading ────────────────────────────────────────────────
        m = _HEADING_RE.match(s)
        if m:
            lvl, title = len(m.group(1)), m.group(2).strip()
            while len(stack) > 1 and stack[-1][0] >= lvl:
                stack.pop()
            sec: dict = {}
            _put(cur(), title, sec)
            stack.append((lvl, sec))
            i += 1
            continue

        # ── table ──────────────────────────────────────────────────
        if s.startswith("|") and s.endswith("|") and s.count("|") >= 3:
            hdrs = [h.strip() for h in s.split("|")[1:-1]]
            i += 1
            if i < n and _TABLE_SEP_RE.match(lines[i]):
                i += 1
            rows: list[dict] = []
            while i < n and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                cells = [c.strip() for c in lines[i].strip().split("|")[1:-1]]
                rows.append({hdrs[j]: _strip_md(cells[j]) if j < len(cells) else "" for j in range(len(hdrs))})
                i += 1
            _put(cur(), "_table", rows)
            continue

        # ── bold key: value ────────────────────────────────────────
        m = _BOLD_KV_RE.match(s)
        if m:
            key, val = m.group(1).strip(), _strip_md(m.group(2))
            i += 1
            # if value is empty, try to merge with a following code block
            if not val:
                j = i
                while j < n and not lines[j].strip():
                    j += 1
                if j < n and lines[j].strip().startswith("```"):
                    lang = lines[j].strip()[3:].strip()
                    buf = []
                    j += 1
                    while j < n and not lines[j].strip().startswith("```"):
                        buf.append(lines[j])
                        j += 1
                    if j < n:
                        j += 1
                    val = "\n".join(buf)
                    i = j
            _put(cur(), key, val)
            continue

        # ── blockquote ─────────────────────────────────────────────
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            _put(cur(), "_note", _strip_md(" ".join(buf)))
            continue

        # ── unordered list ─────────────────────────────────────────
        if _UL_RE.match(s):
            items: list[str] = []
            while i < n and (ul_m := _UL_RE.match(lines[i].strip())):
                items.append(_strip_md(ul_m.group(1)))
                i += 1
            _put(cur(), "_items", items)
            continue

        # ── ordered list ───────────────────────────────────────────
        if _OL_RE.match(s):
            items = []
            while i < n and (ol_m := _OL_RE.match(lines[i].strip())):
                items.append(_strip_md(ol_m.group(1)))
                i += 1
            _put(cur(), "_items", items)
            continue

        # ── plain text paragraph ───────────────────────────────────
        buf = []
        while i < n:
            ln = lines[i].strip()
            if (
                not ln
                or ln.startswith(("#", "|", "```", ">"))
                or _UL_RE.match(ln)
                or _OL_RE.match(ln)
                or _BOLD_KV_RE.match(ln)
                or _HR_RE.match(ln)
            ):
                break
            buf.append(ln)
            i += 1
        if buf:
            _put(cur(), "_text", _strip_md(" ".join(buf)))

    return _simplify(root)


def _simplify(obj) -> Any:
    """Collapse single-child internal nodes and clean up temp keys.

    * A dict whose *only* keys are internal (``_table``, ``_items``,
      ``_text``, ``_note``) and there is exactly one such key is replaced
      by that key's value (unwrapped).
    * Otherwise internal keys are renamed (leading ``_`` removed).
    """
    if not isinstance(obj, dict):
        return obj

    result = {k: _simplify(v) if isinstance(v, dict) else v for k, v in obj.items()}

    internal = [k for k in result if k.startswith("_")]
    regular = [k for k in result if not k.startswith("_")]

    # single anonymous block, no named children → unwrap
    if not regular and len(internal) == 1:
        return result[internal[0]]

    # rename remaining internal keys
    for k in internal:
        clean = k[1:]
        if clean not in result:
            result[clean] = result.pop(k)

    return result


_PAGE_REGISTRY: dict[int, dict[int, tuple[str, str]]] = {
    # type 1 — subscription plans
    1: {
        0: ("subscriptions", "README.md"),
        1: ("subscriptions", "free.md"),
        2: ("subscriptions", "eod-historical-data-all-world.md"),
        3: ("subscriptions", "eod-intraday-all-world-extended.md"),
        4: ("subscriptions", "fundamentals-data-feed.md"),
        5: ("subscriptions", "all-in-one.md"),
        6: ("subscriptions", "all-in-one-extended-fundamentals.md"),
        7: ("subscriptions", "calendar-feed.md"),
    },
    # type 2 — endpoint documentation
    2: {
        0: ("endpoints", "README.md"),
        1: ("endpoints", "bulk-fundamentals.md"),
        2: ("endpoints", "cboe-index-data.md"),
        3: ("endpoints", "cboe-indices-list.md"),
        4: ("endpoints", "company-news.md"),
        5: ("endpoints", "earnings-trends.md"),
        6: ("endpoints", "economic-events.md"),
        7: ("endpoints", "exchange-details.md"),
        8: ("endpoints", "exchange-tickers.md"),
        9: ("endpoints", "exchanges-list.md"),
        10: ("endpoints", "fundamentals-data.md"),
        11: ("endpoints", "historical-market-cap.md"),
        12: ("endpoints", "historical-stock-prices.md"),
        13: ("endpoints", "illio-market-insights-best-worst.md"),
        14: ("endpoints", "illio-market-insights-beta-bands.md"),
        15: ("endpoints", "illio-market-insights-largest-volatility.md"),
        16: ("endpoints", "illio-market-insights-performance.md"),
        17: ("endpoints", "illio-market-insights-risk-return.md"),
        18: ("endpoints", "illio-market-insights-volatility.md"),
        19: ("endpoints", "illio-performance-insights.md"),
        20: ("endpoints", "illio-risk-insights.md"),
        21: ("endpoints", "index-components.md"),
        22: ("endpoints", "indices-list.md"),
        23: ("endpoints", "insider-transactions.md"),
        24: ("endpoints", "intraday-historical-data.md"),
        25: ("endpoints", "investverte-esg-list-companies.md"),
        26: ("endpoints", "investverte-esg-list-countries.md"),
        27: ("endpoints", "investverte-esg-list-sectors.md"),
        28: ("endpoints", "investverte-esg-view-company.md"),
        29: ("endpoints", "investverte-esg-view-country.md"),
        30: ("endpoints", "investverte-esg-view-sector.md"),
        31: ("endpoints", "live-price-data.md"),
        32: ("endpoints", "macro-indicator.md"),
        33: ("endpoints", "marketplace-tick-data.md"),
        34: ("endpoints", "news-word-weights.md"),
        35: ("endpoints", "praams-bank-balance-sheet-by-isin.md"),
        36: ("endpoints", "praams-bank-balance-sheet-by-ticker.md"),
        37: ("endpoints", "praams-bank-income-statement-by-isin.md"),
        38: ("endpoints", "praams-bank-income-statement-by-ticker.md"),
        39: ("endpoints", "praams-bond-analyze-by-isin.md"),
        40: ("endpoints", "praams-report-bond-by-isin.md"),
        41: ("endpoints", "praams-report-equity-by-isin.md"),
        42: ("endpoints", "praams-report-equity-by-ticker.md"),
        43: ("endpoints", "praams-risk-scoring-by-isin.md"),
        44: ("endpoints", "praams-risk-scoring-by-ticker.md"),
        45: ("endpoints", "praams-smart-investment-screener-bond.md"),
        46: ("endpoints", "praams-smart-investment-screener-equity.md"),
        47: ("endpoints", "sentiment-data.md"),
        48: ("endpoints", "stock-market-logos.md"),
        49: ("endpoints", "stock-market-logos-svg.md"),
        50: ("endpoints", "stock-screener-data.md"),
        51: ("endpoints", "stocks-from-search.md"),
        52: ("endpoints", "symbol-change-history.md"),
        53: ("endpoints", "technical-indicators.md"),
        54: ("endpoints", "tradinghours-list-markets.md"),
        55: ("endpoints", "tradinghours-lookup-markets.md"),
        56: ("endpoints", "tradinghours-market-details.md"),
        57: ("endpoints", "tradinghours-market-status.md"),
        58: ("endpoints", "upcoming-dividends.md"),
        59: ("endpoints", "upcoming-earnings.md"),
        60: ("endpoints", "upcoming-ipos.md"),
        61: ("endpoints", "upcoming-splits.md"),
        62: ("endpoints", "us-live-extended-quotes.md"),
        63: ("endpoints", "us-options-contracts.md"),
        64: ("endpoints", "us-options-eod.md"),
        65: ("endpoints", "us-options-underlyings.md"),
        66: ("endpoints", "us-tick-data.md"),
        67: ("endpoints", "ust-bill-rates.md"),
        68: ("endpoints", "ust-long-term-rates.md"),
        69: ("endpoints", "ust-real-yield-rates.md"),
        70: ("endpoints", "ust-yield-rates.md"),
        71: ("endpoints", "user-details.md"),
        72: ("endpoints", "websockets-realtime.md"),
    },
    # type 3 — general reference
    3: {
        0: ("general", "README.md"),
        1: ("general", "api-authentication-demo-access.md"),
        2: ("general", "authentication.md"),
        3: ("general", "crypto-data-notes.md"),
        4: ("general", "data-adjustment-guide.md"),
        5: ("general", "delisted-tickers-guide.md"),
        6: ("general", "exchanges.md"),
        7: ("general", "financial-ratios-calculation-guide.md"),
        8: ("general", "forex-data-notes.md"),
        9: ("general", "fundamentals-api.md"),
        10: ("general", "fundamentals-common-stock.md"),
        11: ("general", "fundamentals-crypto-currency.md"),
        12: ("general", "fundamentals-etf.md"),
        13: ("general", "fundamentals-etf-metrics.md"),
        14: ("general", "fundamentals-faq.md"),
        15: ("general", "fundamentals-fund.md"),
        16: ("general", "fundamentals-ratios.md"),
        17: ("general", "general-data-faq.md"),
        18: ("general", "glossary.md"),
        19: ("general", "indices-data-notes.md"),
        20: ("general", "pricing-and-plans.md"),
        21: ("general", "primary-tickers-guide.md"),
        22: ("general", "rate-limits.md"),
        23: ("general", "sdks-and-integrations.md"),
        24: ("general", "special-exchanges-guide.md"),
        25: ("general", "stock-types-ticker-suffixes-guide.md"),
        26: ("general", "symbol-format.md"),
        27: ("general", "update-times.md"),
        28: ("general", "versioning.md"),
    },
}


def _serve_global_readme(fallback: bool = False) -> str:
    """Return the global README, optionally flagged as a fallback."""
    file_path = _RESOURCES_DIR / "README.md"
    if not file_path.is_file():
        raise ToolError("Global README not found.")
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as e:
        raise ToolError(f"Failed to read global README: {e}")
    try:
        structured = _parse_markdown(content)
    except Exception as e:
        structured = {"parsing_error": str(e)}
    result = {"type": 0, "id": 0, "title": "Global Readme", "content": structured, "raw": content}
    if fallback:
        result["fallback"] = True
    return json.dumps(result, indent=2)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def retrieve_description_by_id(
        type: int | str | None = 0,
        id: int | str | None = None,
        api_token: str | None = None,  # noqa: ARG001 — kept for MCP tool interface parity
    ) -> str:
        """

        Retrieve built-in EODHD API documentation by numeric type and id. Use when
        the user asks about API usage, endpoint specs, subscription plans, or reference guides.
        Returns structured Markdown content for subscriptions (type=1), endpoint docs (type=2),
        or general reference (type=3). Call with type=0 or no args for the global README index.
        This is a local lookup — not an API data call. No API calls consumed.

        Types:
          0 — Global README / help
          1 — Subscription plans (ids 1-7; id 0 = subscriptions README)
          2 — Endpoint documentation (ids 1-72; id 0 = endpoints README)
          3 — General reference (ids 1-28; id 0 = general README)

        Subscription plan pages (type=1):
          1 — Free, 2 — EOD Historical Data All World,
          3 — EOD Intraday All World Extended, 4 — Fundamentals Data Feed,
          5 — All-In-One, 6 — All-In-One Extended Fundamentals,
          7 — Calendar Feed

        Endpoint documentation pages (type=2):
          1 — Bulk Fundamentals, 2 — CBOE Index Data, 3 — CBOE Indices List,
          4 — Company News, 5 — Earnings Trends, 6 — Economic Events,
          7 — Exchange Details, 8 — Exchange Tickers, 9 — Exchanges List,
          10 — Fundamentals Data, 11 — Historical Market Cap,
          12 — Historical Stock Prices, 13-20 — Illio insights,
          21 — Index Components, 22 — Indices List, 23 — Insider Transactions,
          24 — Intraday Historical Data, 25-30 — Investverte ESG,
          31 — Live Price Data, 32 — Macro Indicator,
          33 — Marketplace Tick Data, 34 — News Word Weights,
          35-46 — PRAAMS endpoints, 47 — Sentiment Data,
          48 — Stock Market Logos, 49 — Stock Market Logos SVG,
          50 — Stock Screener Data, 51 — Stocks From Search,
          52 — Symbol Change History, 53 — Technical Indicators,
          54-57 — Trading Hours, 58 — Upcoming Dividends,
          59 — Upcoming Earnings, 60 — Upcoming IPOs,
          61 — Upcoming Splits, 62 — US Live Extended Quotes,
          63-65 — US Options, 66 — US Tick Data, 67-70 — UST Rates,
          71 — User Details, 72 — WebSockets Realtime

        General reference pages (type=3):
          1 — API Authentication Demo Access, 2 — Authentication,
          3 — Crypto Data Notes, 4 — Data Adjustment Guide,
          5 — Delisted Tickers Guide, 6 — Exchanges,
          7 — Financial Ratios Calculation Guide, 8 — Forex Data Notes,
          9-16 — Fundamentals guides, 17 — General Data FAQ,
          18 — Glossary, 19 — Indices Data Notes,
          20 — Pricing And Plans, 21 — Primary Tickers Guide,
          22 — Rate Limits, 23 — SDKs And Integrations,
          24 — Special Exchanges Guide,
          25 — Stock Types Ticker Suffixes Guide,
          26 — Symbol Format, 27 — Update Times, 28 — Versioning

        Args:
            type: Page category (0 = global README, 1 = subscriptions,
                  2 = endpoints, 3 = general). Default 0.
            id: Numeric page ID within the type. Optional; defaults to 0
                (README for the given type).
            api_token: Ignored (accepted for interface uniformity).

        Returns:
            JSON object with:
            - type (int): Page category number (0-3).
            - id (int): Page ID within the category.
            - title (str): Human-readable page title derived from filename.
            - content (dict): Structured parsed markdown (headings as nested dicts,
              tables as list-of-dicts, lists as arrays, key-value pairs as dict entries).
            - raw (str): Original markdown source text.
            - fallback (bool, optional): Present and true when invalid/missing params
              caused a fallback to the global README.

        Examples:
            "show me the global help page" → type=0
            "docs for the All-In-One subscription plan" → type=1, id=5
            "how does the historical stock prices endpoint work" → type=2, id=12
            "explain rate limits" → type=3, id=22


        """
        if type is None:
            page_type = 0
        else:
            try:
                page_type = int(type)
            except (ValueError, TypeError):
                return _serve_global_readme(fallback=True)

        if page_type == 0:
            return _serve_global_readme(fallback=False)

        pages = _PAGE_REGISTRY.get(page_type)
        if pages is None:
            return _serve_global_readme(fallback=True)

        if id is None:
            page_id = 0
        else:
            try:
                page_id = int(id)
            except (ValueError, TypeError):
                return _serve_global_readme(fallback=True)

        entry = pages.get(page_id)
        if entry is None:
            return _serve_global_readme(fallback=True)

        subdir, filename = entry
        file_path = _RESOURCES_DIR / subdir / filename
        if not file_path.is_file():
            raise ToolError(f"Documentation file not found for type {page_type}, id {page_id}.")

        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError as e:
            raise ToolError(f"Failed to read documentation file: {e}")

        title = Path(filename).stem.replace("-", " ").replace("_", " ").title()

        try:
            structured = _parse_markdown(content)
        except Exception as e:
            structured = {"parsing_error": str(e)}

        return json.dumps(
            {"type": page_type, "id": page_id, "title": title, "content": structured, "raw": content},
            indent=2,
        )
