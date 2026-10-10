# app/tools/get_rates_funding_stress.py


import logging

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import (
    build_query_param,
    build_url,
    coerce_date_param,
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
    @mcp.tool(annotations=ToolAnnotations(title="Interest Rates: Funding-Stress Spreads", readOnlyHint=True))
    async def get_rates_funding_stress(
        code: str | None = None,  # filter[code], e.g. EFFR_SOFR spread
        date_from: str | None = None,  # filter[from], YYYY-MM-DD
        date_to: str | None = None,  # filter[to], YYYY-MM-DD
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch funding-stress spreads. Use when the user asks about money-market funding stress,
        rate spreads between two legs (e.g. EFFR minus SOFR for code EFFR_SOFR), or funding-stress
        indicators in basis points.

        Returns funding-stress spread time series, including the two component legs and their
        rates. Filterable by code and date range. This endpoint is NOT paginated. If no dates are
        given, the most recent 30 days are returned.

        Args:
            code (str, optional): Spread code — one of 'EFFR_SOFR', 'OBFR_EFFR', 'TGCR_BGCR',
                'SOFR_TARGET_LOWER', 'EFFR_TARGET_MID', 'TARGET_UPPER_SOFR'.
            date_from (str, optional): Start date filter (YYYY-MM-DD).
            date_to (str, optional): End date filter (YYYY-MM-DD).
            api_token (str, optional): Per-call token override.


        Returns:
            JSON envelope {data, meta, links}. Each data item:
            - date (str): observation date (YYYY-MM-DD)
            - code (str): spread code
            - value_bps (float): spread value in basis points
            - formula (str): spread formula
            - leg_a (str): first leg code
            - leg_b (str): second leg code
            - leg_a_rate (float): first leg rate
            - leg_b_rate (float): second leg rate

        Examples:
            "EFFR-SOFR funding stress spread" → get_rates_funding_stress(code="EFFR_SOFR")
            "Funding stress for 2025" → get_rates_funding_stress(date_from="2025-01-01", date_to="2025-12-31")
        """
        code = normalize_csv_upper(code)
        date_from = coerce_date_param(date_from, "date_from")
        date_to = coerce_date_param(date_to, "date_to")
        validate_date_range(date_from, date_to, "date_from", "date_to")

        url = build_url(
            "spreads/funding-stress",
            {"api_token": api_token},
        )
        url += build_query_param("filter[code]", code)
        url += build_query_param("filter[from]", date_from)
        url += build_query_param("filter[to]", date_to)

        data = await make_request(url)
        raise_on_api_error(data)

        return format_json_response(data)
