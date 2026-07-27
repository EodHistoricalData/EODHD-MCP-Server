# app/tools/get_rates_policy_rates.py


import logging

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import (
    build_query_param,
    build_url,
    coerce_date_param,
    coerce_page_params,
    normalize_csv_upper,
    validate_date_range,
)
from app.response_formatter import (
    ResourceResponse,
    format_json_response,
    raise_on_api_error,
)

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Interest Rates: Central-Bank Policy Rates", readOnlyHint=True))
    async def get_rates_policy_rates(
        code: str | None = None,  # filter[code]: e.g. FED_TARGET_LOWER, ECB_DFR, BOE_BANK_RATE
        country: str | None = None,  # filter[country]: US | EU | GB
        central_bank: str | None = None,  # filter[central_bank]: FED | ECB | BOE
        date_from: str | None = None,  # filter[from], YYYY-MM-DD
        date_to: str | None = None,  # filter[to], YYYY-MM-DD
        limit: int | str | None = None,  # page[limit], default 20, max 100
        offset: int | str | None = None,  # page[offset]
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch central bank policy rates. Use when the user asks about policy interest rates set by
        central banks (e.g. Fed funds rate, ECB, Bank of England), or policy rate history by
        country or central bank.

        Returns central bank policy rate time series. Filterable by code, country, central bank,
        and date range. Paginated.

        Args:
            code (str, optional): Rate code — one of 'FED_TARGET_LOWER', 'FED_TARGET_UPPER',
                'ECB_DFR', 'ECB_MRO', 'ECB_MLF', 'BOE_BANK_RATE' (comma-separated list allowed).
            country (str, optional): Country: 'US', 'EU', or 'GB' (comma-separated list allowed).
            central_bank (str, optional): Central bank: 'FED', 'ECB', or 'BOE' (comma-separated list allowed).
            date_from (str, optional): Start date filter (YYYY-MM-DD).
            date_to (str, optional): End date filter (YYYY-MM-DD).
            limit (int, optional): Records per page (default 20, max 100).
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override.


        Returns:
            JSON envelope {data, meta, links}. Each data item:
            - date (str): observation date (YYYY-MM-DD)
            - code (str): rate code
            - country (str): country
            - central_bank (str): central bank
            - rate (float): policy rate
            - source (str): data source
            - source_series_id (str): upstream series identifier

        Examples:
            "Fed funds policy rate history" → get_rates_policy_rates(central_bank="FED")
            "ECB policy rate for 2025" → get_rates_policy_rates(country="EU", date_from="2025-01-01")
        """
        code = normalize_csv_upper(code)
        country = normalize_csv_upper(country)
        central_bank = normalize_csv_upper(central_bank)
        date_from = coerce_date_param(date_from, "date_from")
        date_to = coerce_date_param(date_to, "date_to")
        validate_date_range(date_from, date_to, "date_from", "date_to")
        lim, off = coerce_page_params(limit, offset)

        url = build_url(
            "rates/policy-rates",
            {"api_token": api_token},
        )
        url += build_query_param("filter[code]", code)
        url += build_query_param("filter[country]", country)
        url += build_query_param("filter[central_bank]", central_bank)
        url += build_query_param("filter[from]", date_from)
        url += build_query_param("filter[to]", date_to)
        url += build_query_param("page[limit]", lim)
        url += build_query_param("page[offset]", off)

        data = await make_request(url)
        raise_on_api_error(data)

        return format_json_response(data)
