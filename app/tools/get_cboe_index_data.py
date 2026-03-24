# app/tools/get_cboe_index_data.py

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_url
from app.response_formatter import ResourceResponse, format_json_response

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_cboe_index_data(
        index_code: str,  # e.g., "BDE30P"
        feed_type: str,  # e.g., "snapshot_official_closing"
        date: str,  # YYYY-MM-DD, e.g., "2017-02-01"
        fmt: str | None = "json",
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Fetch detailed data for a specific CBOE index on a given date, including all constituent
        components. Use when the user needs index close value, divisor, and full component
        breakdown (symbols, weights, market caps, sectors) for a CBOE index.

        Requires index_code, feed_type, and date. Returns index-level attributes plus an array
        of components with ISIN, closing price, currency, shares, market cap, weighting, and
        sector. Costs 10 API calls per request.

        For listing all available CBOE indices, use get_cboe_indices_list first.

        Args:
            index_code (str): CBOE index code (e.g., 'BDE30P', 'BAT20N').
            feed_type (str): Feed type (e.g., 'snapshot_official_closing').
            date (str): Trading date in YYYY-MM-DD format.
            fmt (str): 'json' only (default).
            api_token (str, optional): Per-call token override.


        Returns:
            Object with:
            - meta (object): total (int) — number of results
            - data (array): index feed objects, each with:
              - id (str): composite key (index_code-date-feed_type)
              - type (str): "cboe-index"
              - attributes (object):
                - region (str): geographic region
                - index_code (str): CBOE index code
                - feed_type (str): feed type
                - date (str): trading date (YYYY-MM-DD)
                - index_close (float): index closing value
                - index_divisor (float): index divisor
                - effective_date (str|null): effective date
                - review_date (str|null): review date
              - components (array): index constituents, each with:
                - id (str): component identifier
                - type (str): "cboe-index-component"
                - attributes (object):
                  - symbol (str): ticker symbol
                  - isin (str): ISIN code
                  - name (str): company name
                  - closing_price (float): component closing price
                  - currency (str): trading currency
                  - total_shares (int): total shares outstanding
                  - market_cap (float): market capitalization
                  - index_weighting (float): weight in index (%)
                  - index_value (float): contributed index value
                  - sector (str): industry sector

        Notes:
            - If required filters are missing, the API returns a JSON error
              under the "errors" key.
            - Rate limits: 10 API calls per request (dataset-specific rule of thumb).

        Examples:
            - /api/cboe/index?filter[index_code]=BDE30P
              &filter[feed_type]=snapshot_official_closing
              &filter[date]=2017-02-01
        """
        # Basic validation
        if not index_code or not isinstance(index_code, str):
            raise ToolError("Parameter 'index_code' is required and must be a non-empty string (e.g., 'BDE30P').")

        if not feed_type or not isinstance(feed_type, str):
            raise ToolError(
                "Parameter 'feed_type' is required and must be a non-empty string (e.g., 'snapshot_official_closing')."
            )

        if not date or not isinstance(date, str):
            raise ToolError(
                "Parameter 'date' is required and must be a non-empty string "
                "in 'YYYY-MM-DD' format (e.g., '2017-02-01')."
            )

        if fmt != "json":
            raise ToolError("Only 'json' is supported by this tool.")

        # Build URL with deep-object-style filter params
        url = build_url(
            "cboe/index",
            {
                "filter[index_code]": index_code,
                "filter[feed_type]": feed_type,
                "filter[date]": date,
                "fmt": fmt,
                "api_token": api_token,
            },
        )

        data = await make_request(url)

        try:
            # For both success and {"errors": {...}} cases, return pretty JSON
            return format_json_response(data)
        except Exception as e:
            logger.debug("API response parse error", exc_info=True)
            raise ToolError("Unexpected response format from API.") from e
