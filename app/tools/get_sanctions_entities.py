# app/tools/get_sanctions_entities.py


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

ALLOWED_TYPES = {"individual", "entity", "vessel", "aircraft"}
_MIN_QUERY_LEN = 2

# NOTE: Sanctions endpoints use BARE query parameters (e.g. `type=`, `program=`),
# NOT bracketed `filter[...]` keys. This differs from the credit-risk and rates
# endpoints and is verified against production. Do not switch to filter[...] here.


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(title="Sanctions/OFAC: Entities", readOnlyHint=True))
    async def get_sanctions_entities(
        source: str | None = None,  # e.g. "ofac"
        type: str | None = None,  # individual | entity | vessel | aircraft
        program: str | None = None,  # sanctions program
        country: str | None = None,  # country
        q: str | None = None,  # free-text search (min 2 chars)
        active: bool | None = None,  # true | false
        limit: int | str | None = None,  # page[limit], default 20, max 100
        offset: int | str | None = None,  # page[offset]
        api_token: str | None = None,  # per-call override
    ) -> ResourceResponse:
        """

        Search sanctioned entities (e.g. OFAC). Use when the user asks about sanctioned
        individuals, companies, vessels, or aircraft, OFAC SDN listings, or entities under a
        specific sanctions program.

        Returns sanctioned entities with aliases, identifiers, programs, and listing status.
        Filterable by source, entity type, program, country, free-text query, and active status.
        Paginated.

        Args:
            source (str, optional): Data source. Currently only 'ofac' is accepted.
            type (str, optional): Entity type: 'individual', 'entity', 'vessel', or 'aircraft'.
            program (str, optional): Sanctions program.
            country (str, optional): Country.
            q (str, optional): Free-text search (minimum 2 characters).
            active (bool, optional): Filter by active listing status. When omitted, only active
                listings are returned; pass False to return ONLY inactive/delisted entries
                (active ones are then excluded). There is no single-call "all" mode.
            limit (int, optional): Records per page (default 20, max 100).
            offset (int, optional): Pagination offset.
            api_token (str, optional): Per-call token override.


        Returns:
            JSON envelope {data, meta, links}. Each data item:
            - source (str): data source
            - source_uid (str): source unique identifier
            - entity_type (str): entity type
            - name (str): entity name
            - programs (list): sanctions programs
            - country (str|null): country
            - remarks (str|null): remarks
            - listed_date (str|null): date listed
            - is_active (bool): active listing status
            - aliases (list): known aliases
            - identifiers (dict): map of identifier type → list of values

        Examples:
            "OFAC sanctioned individuals in Russia" → get_sanctions_entities(source="ofac", type="individual", country="Russia")
            "Search sanctioned entities for 'Gazprom'" → get_sanctions_entities(q="Gazprom")
        """
        if type is not None and type not in ALLOWED_TYPES:
            raise ToolError(f"Parameter 'type' must be one of {sorted(ALLOWED_TYPES)}.")

        if q is not None and len(q.strip()) < _MIN_QUERY_LEN:
            raise ToolError(f"Parameter 'q' must be at least {_MIN_QUERY_LEN} characters.")

        lim, off = coerce_page_params(limit, offset)

        url = build_url(
            "sanctions/entities",
            {"api_token": api_token},
        )
        # Bare params (NOT filter[...]) — verified against production.
        url += build_query_param("source", source)
        url += build_query_param("type", type)
        url += build_query_param("program", program)
        url += build_query_param("country", country)
        url += build_query_param("q", q)
        if active is not None:
            url += build_query_param("active", "true" if active else "false")
        url += build_query_param("page[limit]", lim)
        url += build_query_param("page[offset]", off)

        data = await make_request(url)
        raise_on_api_error(data)

        return format_json_response(data)
