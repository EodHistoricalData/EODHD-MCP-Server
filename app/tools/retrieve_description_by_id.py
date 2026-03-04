import json
import re
from pathlib import Path
from typing import Optional, Union

from fastmcp import FastMCP
from mcp.types import ToolAnnotations


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)


_RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources" / "references"

# ---------------------------------------------------------------------------
# Markdown → nested-dict parser
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)')
_BOLD_KV_RE = re.compile(r'^\*\*(.+?)\*\*\s*:\s*(.*)')
_UL_RE = re.compile(r'^[-*]\s+(.*)')
_OL_RE = re.compile(r'^\d+\.\s+(.*)')
_TABLE_SEP_RE = re.compile(r'^\s*\|[\s\-:|]+\|\s*$')
_HR_RE = re.compile(r'^[-*_]{3,}\s*$')


def _strip_md(text: str) -> str:
    """Remove inline markdown formatting, keeping plain text."""
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)   # [link](url)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)            # **bold**
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)',
                  r'\1', text)                               # *italic*
    text = re.sub(r'`(.+?)`', r'\1', text)                  # `code`
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


def _parse_markdown(text: str) -> dict:
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
    lines = text.split('\n')
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
        if s.startswith('```'):
            lang = s[3:].strip()
            buf: list[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1
            if i < n:
                i += 1
            key = f"example_{lang}" if lang else "example"
            _put(cur(), key, '\n'.join(buf))
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
        if s.startswith('|') and s.endswith('|') and s.count('|') >= 3:
            hdrs = [h.strip() for h in s.split('|')[1:-1]]
            i += 1
            if i < n and _TABLE_SEP_RE.match(lines[i]):
                i += 1
            rows: list[dict] = []
            while (i < n
                   and lines[i].strip().startswith('|')
                   and lines[i].strip().endswith('|')):
                cells = [c.strip()
                         for c in lines[i].strip().split('|')[1:-1]]
                rows.append({
                    hdrs[j]: _strip_md(cells[j]) if j < len(cells) else ""
                    for j in range(len(hdrs))
                })
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
                if j < n and lines[j].strip().startswith('```'):
                    lang = lines[j].strip()[3:].strip()
                    buf = []
                    j += 1
                    while j < n and not lines[j].strip().startswith('```'):
                        buf.append(lines[j])
                        j += 1
                    if j < n:
                        j += 1
                    val = '\n'.join(buf)
                    i = j
            _put(cur(), key, val)
            continue

        # ── blockquote ─────────────────────────────────────────────
        if s.startswith('>'):
            buf = []
            while i < n and lines[i].strip().startswith('>'):
                buf.append(lines[i].strip().lstrip('>').strip())
                i += 1
            _put(cur(), "_note", _strip_md(' '.join(buf)))
            continue

        # ── unordered list ─────────────────────────────────────────
        if _UL_RE.match(s):
            items: list[str] = []
            while i < n and _UL_RE.match(lines[i].strip()):
                items.append(
                    _strip_md(_UL_RE.match(lines[i].strip()).group(1)))
                i += 1
            _put(cur(), "_items", items)
            continue

        # ── ordered list ───────────────────────────────────────────
        if _OL_RE.match(s):
            items = []
            while i < n and _OL_RE.match(lines[i].strip()):
                items.append(
                    _strip_md(_OL_RE.match(lines[i].strip()).group(1)))
                i += 1
            _put(cur(), "_items", items)
            continue

        # ── plain text paragraph ───────────────────────────────────
        buf = []
        while i < n:
            ln = lines[i].strip()
            if (not ln
                    or ln.startswith(('#', '|', '```', '>'))
                    or _UL_RE.match(ln) or _OL_RE.match(ln)
                    or _BOLD_KV_RE.match(ln) or _HR_RE.match(ln)):
                break
            buf.append(ln)
            i += 1
        if buf:
            _put(cur(), "_text", _strip_md(' '.join(buf)))

    return _simplify(root)


def _simplify(obj):
    """Collapse single-child internal nodes and clean up temp keys.

    * A dict whose *only* keys are internal (``_table``, ``_items``,
      ``_text``, ``_note``) and there is exactly one such key is replaced
      by that key's value (unwrapped).
    * Otherwise internal keys are renamed (leading ``_`` removed).
    """
    if not isinstance(obj, dict):
        return obj

    result = {
        k: _simplify(v) if isinstance(v, dict) else v
        for k, v in obj.items()
    }

    internal = [k for k in result if k.startswith('_')]
    regular = [k for k in result if not k.startswith('_')]

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
    # type 0 — subscription plans
    0: {
        0: ("subscriptions", "free.md"),
        1: ("subscriptions", "eod-historical-data-all-world.md"),
        2: ("subscriptions", "eod-intraday-all-world-extended.md"),
        3: ("subscriptions", "fundamentals-data-feed.md"),
        4: ("subscriptions", "all-in-one.md"),
        5: ("subscriptions", "all-in-one-extended-fundamentals.md"),
        6: ("subscriptions", "calendar-feed.md"),
    },
    # type 1 — endpoint documentation
    1: {
        0: ("endpoints", "bulk-fundamentals.md"),
        1: ("endpoints", "cboe-index-data.md"),
        2: ("endpoints", "cboe-indices-list.md"),
        3: ("endpoints", "company-news.md"),
        4: ("endpoints", "earnings-trends.md"),
        5: ("endpoints", "economic-events.md"),
        6: ("endpoints", "exchange-details.md"),
        7: ("endpoints", "exchange-tickers.md"),
        8: ("endpoints", "exchanges-list.md"),
        9: ("endpoints", "fundamentals-data.md"),
        10: ("endpoints", "historical-market-cap.md"),
        11: ("endpoints", "historical-stock-prices.md"),
        12: ("endpoints", "illio-market-insights-best-worst.md"),
        13: ("endpoints", "illio-market-insights-beta-bands.md"),
        14: ("endpoints", "illio-market-insights-largest-volatility.md"),
        15: ("endpoints", "illio-market-insights-performance.md"),
        16: ("endpoints", "illio-market-insights-risk-return.md"),
        17: ("endpoints", "illio-market-insights-volatility.md"),
        18: ("endpoints", "illio-performance-insights.md"),
        19: ("endpoints", "illio-risk-insights.md"),
        20: ("endpoints", "index-components.md"),
        21: ("endpoints", "indices-list.md"),
        22: ("endpoints", "insider-transactions.md"),
        23: ("endpoints", "intraday-historical-data.md"),
        24: ("endpoints", "investverte-esg-list-companies.md"),
        25: ("endpoints", "investverte-esg-list-countries.md"),
        26: ("endpoints", "investverte-esg-list-sectors.md"),
        27: ("endpoints", "investverte-esg-view-company.md"),
        28: ("endpoints", "investverte-esg-view-country.md"),
        29: ("endpoints", "investverte-esg-view-sector.md"),
        30: ("endpoints", "live-price-data.md"),
        31: ("endpoints", "macro-indicator.md"),
        32: ("endpoints", "marketplace-tick-data.md"),
        33: ("endpoints", "news-word-weights.md"),
        34: ("endpoints", "praams-bank-balance-sheet-by-isin.md"),
        35: ("endpoints", "praams-bank-balance-sheet-by-ticker.md"),
        36: ("endpoints", "praams-bank-income-statement-by-isin.md"),
        37: ("endpoints", "praams-bank-income-statement-by-ticker.md"),
        38: ("endpoints", "praams-bond-analyze-by-isin.md"),
        39: ("endpoints", "praams-report-bond-by-isin.md"),
        40: ("endpoints", "praams-report-equity-by-isin.md"),
        41: ("endpoints", "praams-report-equity-by-ticker.md"),
        42: ("endpoints", "praams-risk-scoring-by-isin.md"),
        43: ("endpoints", "praams-risk-scoring-by-ticker.md"),
        44: ("endpoints", "praams-smart-investment-screener-bond.md"),
        45: ("endpoints", "praams-smart-investment-screener-equity.md"),
        46: ("endpoints", "sentiment-data.md"),
        47: ("endpoints", "stock-market-logos.md"),
        48: ("endpoints", "stock-market-logos-svg.md"),
        49: ("endpoints", "stock-screener-data.md"),
        50: ("endpoints", "stocks-from-search.md"),
        51: ("endpoints", "symbol-change-history.md"),
        52: ("endpoints", "technical-indicators.md"),
        53: ("endpoints", "tradinghours-list-markets.md"),
        54: ("endpoints", "tradinghours-lookup-markets.md"),
        55: ("endpoints", "tradinghours-market-details.md"),
        56: ("endpoints", "tradinghours-market-status.md"),
        57: ("endpoints", "upcoming-dividends.md"),
        58: ("endpoints", "upcoming-earnings.md"),
        59: ("endpoints", "upcoming-ipos.md"),
        60: ("endpoints", "upcoming-splits.md"),
        61: ("endpoints", "us-live-extended-quotes.md"),
        62: ("endpoints", "us-options-contracts.md"),
        63: ("endpoints", "us-options-eod.md"),
        64: ("endpoints", "us-options-underlyings.md"),
        65: ("endpoints", "us-tick-data.md"),
        66: ("endpoints", "ust-bill-rates.md"),
        67: ("endpoints", "ust-long-term-rates.md"),
        68: ("endpoints", "ust-real-yield-rates.md"),
        69: ("endpoints", "ust-yield-rates.md"),
        70: ("endpoints", "user-details.md"),
        71: ("endpoints", "websockets-realtime.md"),
    },
    # type 2 — general reference
    2: {
        0: ("general", "api-authentication-demo-access.md"),
        1: ("general", "authentication.md"),
        2: ("general", "crypto-data-notes.md"),
        3: ("general", "data-adjustment-guide.md"),
        4: ("general", "delisted-tickers-guide.md"),
        5: ("general", "exchanges.md"),
        6: ("general", "financial-ratios-calculation-guide.md"),
        7: ("general", "forex-data-notes.md"),
        8: ("general", "fundamentals-api.md"),
        9: ("general", "fundamentals-common-stock.md"),
        10: ("general", "fundamentals-crypto-currency.md"),
        11: ("general", "fundamentals-etf.md"),
        12: ("general", "fundamentals-etf-metrics.md"),
        13: ("general", "fundamentals-faq.md"),
        14: ("general", "fundamentals-fund.md"),
        15: ("general", "fundamentals-ratios.md"),
        16: ("general", "general-data-faq.md"),
        17: ("general", "glossary.md"),
        18: ("general", "indices-data-notes.md"),
        19: ("general", "pricing-and-plans.md"),
        20: ("general", "primary-tickers-guide.md"),
        21: ("general", "rate-limits.md"),
        22: ("general", "sdks-and-integrations.md"),
        23: ("general", "special-exchanges-guide.md"),
        24: ("general", "stock-types-ticker-suffixes-guide.md"),
        25: ("general", "symbol-format.md"),
        26: ("general", "update-times.md"),
        27: ("general", "versioning.md"),
    },
}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def retrieve_description_by_id(
        id: Union[int, str],
        type: Union[int, str] = 0,
        api_token: Optional[str] = None,
    ) -> str:
        """
        Returns a predefined documentation page by numeric ID and type.

        Types:
          0 — Subscription plans (7 pages, ids 0-6)
          1 — Endpoint documentation (72 pages, ids 0-71)
          2 — General reference (28 pages, ids 0-27)

        Subscription plan pages (type=0):
          0 — Free, 1 — EOD Historical Data All World,
          2 — EOD Intraday All World Extended, 3 — Fundamentals Data Feed,
          4 — All-In-One, 5 — All-In-One Extended Fundamentals,
          6 — Calendar Feed

        Endpoint documentation pages (type=1):
          0 — Bulk Fundamentals, 1 — CBOE Index Data, 2 — CBOE Indices List,
          3 — Company News, 4 — Earnings Trends, 5 — Economic Events,
          6 — Exchange Details, 7 — Exchange Tickers, 8 — Exchanges List,
          9 — Fundamentals Data, 10 — Historical Market Cap,
          11 — Historical Stock Prices, 12-19 — Illio insights,
          20 — Index Components, 21 — Indices List, 22 — Insider Transactions,
          23 — Intraday Historical Data, 24-29 — Investverte ESG,
          30 — Live Price Data, 31 — Macro Indicator,
          32 — Marketplace Tick Data, 33 — News Word Weights,
          34-45 — PRAAMS endpoints, 46 — Sentiment Data,
          47 — Stock Market Logos, 48 — Stock Market Logos SVG,
          49 — Stock Screener Data, 50 — Stocks From Search,
          51 — Symbol Change History, 52 — Technical Indicators,
          53-56 — Trading Hours, 57 — Upcoming Dividends,
          58 — Upcoming Earnings, 59 — Upcoming IPOs,
          60 — Upcoming Splits, 61 — US Live Extended Quotes,
          62-64 — US Options, 65 — US Tick Data, 66-69 — UST Rates,
          70 — User Details, 71 — WebSockets Realtime

        General reference pages (type=2):
          0 — API Authentication Demo Access, 1 — Authentication,
          2 — Crypto Data Notes, 3 — Data Adjustment Guide,
          4 — Delisted Tickers Guide, 5 — Exchanges,
          6 — Financial Ratios Calculation Guide, 7 — Forex Data Notes,
          8-15 — Fundamentals guides, 16 — General Data FAQ,
          17 — Glossary, 18 — Indices Data Notes,
          19 — Pricing And Plans, 20 — Primary Tickers Guide,
          21 — Rate Limits, 22 — SDKs And Integrations,
          23 — Special Exchanges Guide,
          24 — Stock Types Ticker Suffixes Guide,
          25 — Symbol Format, 26 — Update Times, 27 — Versioning

        Args:
            id: Numeric ID of the documentation page.
            type: Page category (0 = subscriptions, 1 = endpoints, 2 = general). Default 0.
            api_token: Ignored (accepted for interface uniformity).

        Returns:
            JSON string with "type", "id", "title", and "content" keys,
            or {"error": "..."} on failure.
        """
        try:
            page_type = int(type)
        except (ValueError, TypeError):
            return _err(f"'type' must be an integer, got: {type!r}")

        pages = _PAGE_REGISTRY.get(page_type)
        if pages is None:
            valid = sorted(_PAGE_REGISTRY.keys())
            return _err(f"Unknown type {page_type}. Valid types: {valid}")

        try:
            page_id = int(id)
        except (ValueError, TypeError):
            return _err(f"'id' must be an integer, got: {id!r}")

        entry = pages.get(page_id)
        if entry is None:
            valid = sorted(pages.keys())
            return _err(f"Unknown page id {page_id} for type {page_type}. Valid ids: {valid}")

        subdir, filename = entry
        file_path = _RESOURCES_DIR / subdir / filename
        if not file_path.is_file():
            return _err(f"Documentation file not found for type {page_type}, id {page_id}.")

        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError as e:
            return _err(f"Failed to read documentation file: {e}")

        title = Path(filename).stem.replace("-", " ").replace("_", " ").title()

        try:
            structured = _parse_markdown(content)
        except Exception as e:
            structured = {"parsing_error": str(e)}

        return json.dumps(
            {"type": page_type, "id": page_id, "title": title,
             "content": structured, "raw": content},
            indent=2,
        )
