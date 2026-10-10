# app/tools/sec_filings.py


import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import (
    build_query_param,
    build_url,
    coerce_page_params,
    sanitize_ticker,
)
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)

MAX_PAGE_LIMIT = 100

# The three list endpoints, keyed by the URL segment EODHD expects. ``None`` (the default)
# selects the overview endpoint, which has no filing segment and no pagination.
_FORMS = ("10k", "10q", "8k")


def _normalize_form(form: str | None) -> str | None:
    """Coerce a filing-type input to the exact segment EODHD's route expects.

    Accepts flexible spellings the agent may produce — ``"10-K"``, ``"10 K"``, ``"Form 8-K"`` —
    and reduces them to ``10k`` / ``10q`` / ``8k``. ``None`` selects the overview endpoint.
    """
    if form is None:
        return None
    normalized = str(form).strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    if normalized.startswith("form"):
        normalized = normalized[len("form") :]
    if normalized not in _FORMS:
        raise ToolError("Parameter 'form' must be one of '10k', '10q', '8k', or omitted for the filings overview.")
    return normalized


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="SEC Filings", readOnlyHint=True))
    async def get_sec_filings(
        symbol: str,  # US-listed ticker, e.g. AAPL or AAPL.US (the .US suffix is optional)
        form: str | None = None,  # None = overview; else "10k" | "10q" | "8k"
        limit: int | str | None = None,  # page[limit], list endpoints only
        offset: int | str | None = None,  # page[offset], list endpoints only
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch parsed US SEC filing data for a company: an overview of what has been filed, or the
        detailed, structured contents of its annual (10-K), quarterly (10-Q), or material-event
        (8-K) filings. Use when the user asks about a company's SEC filings, its 10-K / 10-Q /
        8-K, annual or quarterly report financials pulled straight from filings, or material events
        disclosed to the SEC.

        Covers US-listed companies. Financial-statement fields in 10-K / 10-Q filings are parsed
        from the filing itself (income statement, balance sheet, cash flow); any individual field
        may be null when the filing does not report it. Requires the All-in-One plan. Costs 10 API
        calls per request.

        This is distinct from the SEC Form 4 insider-transaction feed — for insider buys and sells
        use the insider-transactions tool instead.

        Args:
            symbol (str): US-listed ticker, e.g. "AAPL" or "AAPL.US". The ".US" suffix is optional.
            form (str, optional): Which filing type to return. Omit for the overview (counts and the
                latest filing of each type). Otherwise "10k" (annual), "10q" (quarterly), or "8k"
                (material events). Flexible spellings like "10-K" or "Form 8-K" are accepted.
            limit (int, optional): Records per page for the list endpoints, 1..100 (default 20
                upstream). Ignored for the overview, which is not paginated.
            offset (int, optional): Pagination offset for the list endpoints (default 0). Ignored
                for the overview.
            api_token (str, optional): Per-call token override.

        Returns:
            Overview (form omitted): a data object with ticker, exchange, name, cik, and a filings
            map keyed by "10k", "10q", "8k", "form4", each holding {count, latest, url}.

            10-K / 10-Q (form="10k"/"10q"): an envelope with data (array of filings), meta
            (total, page{offset,limit}), and links (next page URL or null). Each filing carries
            accession_number, filed_at, period_of_report, fiscal_year_end (10-K) or
            fiscal_quarter_end + fiscal_quarter (10-Q), plus parsed income-statement, balance-sheet
            and cash-flow fields (revenue, net_income, ebitda, eps_basic, total_assets,
            stockholders_equity, operating_cash_flow, free_cash_flow, and many more; any may be null).

            8-K (form="8k"): the same envelope; each item carries accession_number, filed_at,
            period_of_report, items (list of item codes), item_sections ({item, title, text}), and
            exhibits ({number, description}).

        Notes:
            - 10 API calls per request.
            - Requires the All-in-One plan.
            - The overview has no pagination; limit/offset apply only to 10k/10q/8k.
            - For Form 4 insider transactions, use the insider-transactions tool, not this one.

        Examples:
            "What has Apple filed with the SEC?" -> get_sec_filings(symbol="AAPL.US")
            "Apple's latest annual report financials" -> get_sec_filings(symbol="AAPL", form="10k", limit=1)
            "Tesla's recent quarterly filings" -> get_sec_filings(symbol="TSLA.US", form="10q")
            "Apple's most recent 8-K material events" -> get_sec_filings(symbol="AAPL", form="8k", limit=5)
        """
        symbol = sanitize_ticker(symbol, param_name="symbol")
        form = _normalize_form(form)

        path = f"sec-filings/{symbol}" if form is None else f"sec-filings/{symbol}/{form}"
        url = build_url(path, {"api_token": api_token})

        # The overview endpoint is not paginated; only the list endpoints accept page[...].
        if form is not None:
            lim, off = coerce_page_params(limit, offset, max_limit=MAX_PAGE_LIMIT)
            url += build_query_param("page[limit]", lim)
            url += build_query_param("page[offset]", off)

        data = await make_request(url)

        try:
            return format_json_response(data)
        except ToolError:
            raise
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
