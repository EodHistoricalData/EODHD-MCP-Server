# app/tools/get_sanctions_vessels.py


import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from app.api_client import make_request
from app.input_formatter import build_query_param, build_url, coerce_page_params
from app.response_formatter import (
    ResourceResponse,
    format_json_response,
    raise_on_api_error,
)

logger = logging.getLogger(__name__)

_MIN_QUERY_LEN = 2

# NOTE: Sanctions endpoints use BARE query parameters (e.g. `imo=`, `flag=`),
# NOT bracketed `filter[...]` keys. This differs from the credit-risk and rates
# endpoints and is verified against production. Do not switch to filter[...] here.


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Sanctions/OFAC: Vessels", readOnlyHint=True))
    async def get_sanctions_vessels(
        source: str | None = None,  # e.g. "ofac"
        imo: str | None = None,  # IMO number
        flag: str | None = None,  # flag state
        vessel_type: str | None = None,  # vessel type
        q: str | None = None,  # free-text search (min 2 chars)
        program: str | None = None,  # sanctions program
        limit: int | str | None = None,  # page[limit], default 20, max 100
        offset: int | str | None = None,  # page[offset]
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Search sanctioned vessels (e.g. OFAC). Use when the user asks about sanctioned ships,
        vessels under sanctions, or vessel details by IMO number, flag, or type.

        Returns sanctioned vessels with identifiers (IMO, MMSI, call sign), flag, tonnage, owner,
        and program context. Filterable by source, IMO, flag, vessel type, free-text query, and
        program. Paginated. Only currently active vessel listings are returned.

        Args:
            source (str, optional): Data source. Currently only 'ofac' is accepted.
            imo (str, optional): IMO number.
            flag (str, optional): Flag state.
            vessel_type (str, optional): Vessel type.
            q (str, optional): Free-text search (minimum 2 characters).
            program (str, optional): Sanctions program.
            limit (int, optional): Records per page (default 20, max 100).
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override.


        Returns:
            JSON envelope {data, meta, links}. Each data item:
            - call_sign (str|null): call sign
            - vessel_type (str|null): vessel type
            - flag (str|null): flag state
            - tonnage (int|null): tonnage
            - gross_tonnage (int|null): gross tonnage
            - owner (str|null): owner
            - imo_number (str|null): IMO number
            - mmsi (str|null): MMSI
            - entity_source_uid (str): linked entity source UID
            - entity_name (str): linked entity name
            - source (str): data source
            - programs (list): sanctions programs
            - country (str|null): country
            - is_active (bool): active listing status

        Examples:
            "Sanctioned vessels flagged Panama" → get_sanctions_vessels(flag="Panama")
            "Vessel with IMO 9160670" → get_sanctions_vessels(imo="9160670")
        """
        if q is not None and len(q.strip()) < _MIN_QUERY_LEN:
            raise ToolError(f"Parameter 'q' must be at least {_MIN_QUERY_LEN} characters.")

        lim, off = coerce_page_params(limit, offset)

        url = build_url(
            "sanctions/vessels",
            {"api_token": api_token},
        )
        # Bare params (NOT filter[...]) — verified against production.
        url += build_query_param("source", source)
        url += build_query_param("imo", imo)
        url += build_query_param("flag", flag)
        url += build_query_param("vessel_type", vessel_type)
        url += build_query_param("q", q)
        url += build_query_param("program", program)
        url += build_query_param("page[limit]", lim)
        url += build_query_param("page[offset]", off)

        data = await make_request(url)
        raise_on_api_error(data)

        return format_json_response(data)
