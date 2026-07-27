# app/tools/get_rates_reference_rates.py


import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import (
    build_query_param,
    build_url,
    coerce_date_param,
    coerce_page_params,
    normalize_csv_upper,
    split_csv,
    validate_date_range,
)
from app.response_formatter import (
    ResourceResponse,
    format_json_response,
    raise_on_api_error,
)

logger = logging.getLogger(__name__)

ALLOWED_CURRENCIES = {"USD", "GBP", "EUR"}


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Interest Rates: Reference Rates", readOnlyHint=True))
    async def get_rates_reference_rates(
        code: str | None = None,  # filter[code], e.g. SOFR, EFFR, SONIA, ESTR (CSV allowed)
        currency: str | None = None,  # filter[currency]: USD | GBP | EUR
        date_from: str | None = None,  # filter[from], YYYY-MM-DD
        date_to: str | None = None,  # filter[to], YYYY-MM-DD
        limit: int | str | None = None,  # page[limit], default 20, max 100
        offset: int | str | None = None,  # page[offset]
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch benchmark reference interest rates. Use when the user asks about reference rates such
        as SOFR, EFFR, SONIA, ESTR, SOFR averages/index, or about overnight rate percentiles and
        traded volumes in USD/GBP/EUR money markets.

        Returns reference rate time series by code and currency, including NY Fed percentiles and
        traded volume where the source publishes them. Filterable by code, currency, and date
        range. Paginated.

        Args:
            code (str, optional): Rate code, or a comma-separated list. Supported codes:
                'SOFR', 'EFFR', 'OBFR', 'TGCR', 'BGCR' (USD overnight), 'SOFR30D', 'SOFR90D',
                'SOFR180D', 'SOFRINDEX' (SOFR averages and compounded index), 'SONIA' (GBP),
                'ESTR' (EUR).
            currency (str, optional): Currency 'USD', 'GBP', or 'EUR' (or a comma-separated list).
            date_from (str, optional): Start date filter (YYYY-MM-DD).
            date_to (str, optional): End date filter (YYYY-MM-DD).
            limit (int, optional): Records per page (default 20, max 100).
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override.


        Returns:
            JSON envelope {data, meta, links}. Each data item:
            - date (str): observation date (YYYY-MM-DD)
            - code (str): rate code
            - currency (str): currency
            - rate_type (str): 'overnight', 'average', or 'index'
            - rate (float): rate value
            - source (str): data source
            - source_series_id (str): upstream series identifier
            - percentiles (dict|null): {p1, p25, p75, p99} distribution, NY Fed rates only
            - volume_billion_usd (float|null): traded volume in USD billions, NY Fed rates only
            - revision_flag (str|null): upstream revision marker

        Examples:
            "SOFR rate history" → get_rates_reference_rates(code="SOFR")
            "EUR reference rates for 2025" → get_rates_reference_rates(currency="EUR", date_from="2025-01-01")
        """
        if currency is not None:
            parts = [c.upper() for c in split_csv(currency)]
            if not parts or any(c not in ALLOWED_CURRENCIES for c in parts):
                raise ToolError(
                    f"Parameter 'currency' must be one (or a comma-separated list) of {sorted(ALLOWED_CURRENCIES)}."
                )
            currency = ",".join(parts)

        code = normalize_csv_upper(code)
        date_from = coerce_date_param(date_from, "date_from")
        date_to = coerce_date_param(date_to, "date_to")
        validate_date_range(date_from, date_to, "date_from", "date_to")
        lim, off = coerce_page_params(limit, offset)

        url = build_url(
            "rates/reference-rates",
            {"api_token": api_token},
        )
        url += build_query_param("filter[code]", code)
        url += build_query_param("filter[currency]", currency)
        url += build_query_param("filter[from]", date_from)
        url += build_query_param("filter[to]", date_to)
        url += build_query_param("page[limit]", lim)
        url += build_query_param("page[offset]", off)

        data = await make_request(url)
        raise_on_api_error(data)

        return format_json_response(data)
