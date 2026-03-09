# get_mp_praams_smart_investment_screener_bond.py

import json
from typing import Any

from app.api_client import make_request
from app.config import EODHD_API_BASE
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _canon_list_ints(v: Any) -> list[int] | None:
    if v is None:
        return None
    if not isinstance(v, (list, tuple)):
        return None
    out: list[int] = []
    for x in v:
        if _is_int(x):
            out.append(int(x))
        elif isinstance(x, str) and x.strip().isdigit():
            out.append(int(x.strip()))
        else:
            return None
    return out


def _canon_list_strs(v: Any) -> list[str] | None:
    if v is None:
        return None
    if not isinstance(v, (list, tuple)):
        return None
    out: list[str] = []
    for x in v:
        if x is None:
            continue
        s = str(x).strip()
        if s:
            out.append(s)
    return out if out else None


def _canon_range_1_7(_name: str, v: Any) -> int | None:
    """
    Canonicalize scoring filters that must be int in [1..7].
    Returns:
      - None if absent
      - int in [1..7] if valid
      - -1 if invalid (caller should return an error)
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    try:
        iv = int(v)
    except Exception:
        return None
    if 1 <= iv <= 7:
        return iv
    return -1


def _canon_int32(v: Any) -> int | None:
    """
    Canonicalize to JSON integer suitable for ASP.NET Int32? binding.

    Accepts:
      - int
      - "123" (string int)
      - 7.0 (float exactly integer)
    Rejects:
      - 7.5 / "7.5"
      - bool
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        if v.is_integer():
            return int(v)
        return None
    if isinstance(v, str):
        s = v.strip()
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            try:
                return int(s)
            except Exception:
                return None
        return None
    try:
        return int(v)
    except Exception:
        return None


def _canon_bool(v: Any) -> bool | None:
    """
    Canonicalize boolean or null.
    Accepts: True/False, 1/0, "true"/"false", "1"/"0"
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, int) and v in (0, 1):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "1", "yes", "y"):
            return True
        if s in ("false", "0", "no", "n"):
            return False
    return None


def _validate_skip_take(skip: Any, take: Any) -> str | None:
    if skip is None:
        return None
    if not _is_int(skip) or skip < 0:
        return "Parameter 'skip' must be an integer >= 0."
    if take is None:
        return None
    if not _is_int(take) or take <= 0:
        return "Parameter 'take' must be an integer > 0."
    return None


def _build_body(
    # ratio / return factors (1..7)
    main_ratio_min: Any = None,
    main_ratio_max: Any = None,
    valuation_min: Any = None,
    valuation_max: Any = None,
    performance_min: Any = None,
    performance_max: Any = None,
    profitability_min: Any = None,
    profitability_max: Any = None,
    growth_mom_min: Any = None,
    growth_mom_max: Any = None,
    other_min: Any = None,
    other_max: Any = None,
    analyst_view_min: Any = None,
    analyst_view_max: Any = None,
    dividends_min: Any = None,
    dividends_max: Any = None,
    market_view_min: Any = None,
    market_view_max: Any = None,
    coupons_min: Any = None,
    coupons_max: Any = None,
    # risk factors (1..7)
    country_risk_min: Any = None,
    country_risk_max: Any = None,
    liquidity_min: Any = None,
    liquidity_max: Any = None,
    stress_test_min: Any = None,
    stress_test_max: Any = None,
    volatility_min: Any = None,
    volatility_max: Any = None,
    solvency_min: Any = None,
    solvency_max: Any = None,
    # geography / classification
    regions: Any = None,
    countries: Any = None,
    sectors: Any = None,
    industries: Any = None,
    capitalisation: Any = None,  # 1/2/3
    currency: Any = None,  # ISO Alpha-3 strings
    # bond-specific numeric ranges (Int32? in schema)
    yield_min: Any = None,
    yield_max: Any = None,
    duration_min: Any = None,
    duration_max: Any = None,
    # bond flags
    exclude_subordinated: Any = None,
    exclude_perpetuals: Any = None,
    # sorting
    order_by: Any = None,
) -> tuple[dict[str, Any] | None, str | None]:
    body: dict[str, Any] = {}

    # --- 1..7 scoring fields ---
    scale_fields = [
        ("mainRatioMin", main_ratio_min),
        ("mainRatioMax", main_ratio_max),
        ("valuationMin", valuation_min),
        ("valuationMax", valuation_max),
        ("performanceMin", performance_min),
        ("performanceMax", performance_max),
        ("profitabilityMin", profitability_min),
        ("profitabilityMax", profitability_max),
        ("growthMomMin", growth_mom_min),
        ("growthMomMax", growth_mom_max),
        ("otherMin", other_min),
        ("otherMax", other_max),
        ("analystViewMin", analyst_view_min),
        ("analystViewMax", analyst_view_max),
        ("dividendsMin", dividends_min),
        ("dividendsMax", dividends_max),
        ("marketViewMin", market_view_min),
        ("marketViewMax", market_view_max),
        ("couponsMin", coupons_min),
        ("couponsMax", coupons_max),
        ("countryRiskMin", country_risk_min),
        ("countryRiskMax", country_risk_max),
        ("liquidityMin", liquidity_min),
        ("liquidityMax", liquidity_max),
        ("stressTestMin", stress_test_min),
        ("stressTestMax", stress_test_max),
        ("volatilityMin", volatility_min),
        ("volatilityMax", volatility_max),
        ("solvencyMin", solvency_min),
        ("solvencyMax", solvency_max),
    ]
    for key, raw in scale_fields:
        v = _canon_range_1_7(key, raw)
        if v is None:
            continue
        if v == -1:
            return None, f"Parameter '{key}' must be an integer in [1..7]."
        body[key] = v

    # --- list fields ---
    li = _canon_list_ints(regions)
    if regions is not None and li is None:
        return None, "Parameter 'regions' must be a list of integers."
    if li:
        body["regions"] = li

    li = _canon_list_ints(countries)
    if countries is not None and li is None:
        return None, "Parameter 'countries' must be a list of integers."
    if li:
        body["countries"] = li

    li = _canon_list_ints(sectors)
    if sectors is not None and li is None:
        return None, "Parameter 'sectors' must be a list of integers."
    if li:
        body["sectors"] = li

    li = _canon_list_ints(industries)
    if industries is not None and li is None:
        return None, "Parameter 'industries' must be a list of integers."
    if li:
        body["industries"] = li

    li = _canon_list_ints(capitalisation)
    if capitalisation is not None and li is None:
        return None, "Parameter 'capitalisation' must be a list of integers (1=small,2=mid,3=large)."
    if li:
        for x in li:
            if x not in (1, 2, 3):
                return None, "Parameter 'capitalisation' values must be in {1,2,3}."
        body["capitalisation"] = li

    ls = _canon_list_strs(currency)
    if currency is not None and ls is None:
        return None, "Parameter 'currency' must be a list of strings (ISO Alpha-3 codes)."
    if ls:
        body["currency"] = ls

    # --- bond numeric ranges (Int32?) ---
    ymi = _canon_int32(yield_min)
    if yield_min is not None and ymi is None:
        return None, "Parameter 'yieldMin' must be an integer."
    if ymi is not None:
        body["yieldMin"] = ymi

    yma = _canon_int32(yield_max)
    if yield_max is not None and yma is None:
        return None, "Parameter 'yieldMax' must be an integer."
    if yma is not None:
        body["yieldMax"] = yma

    dmi = _canon_int32(duration_min)
    if duration_min is not None and dmi is None:
        return None, "Parameter 'durationMin' must be an integer."
    if dmi is not None:
        body["durationMin"] = dmi

    dma = _canon_int32(duration_max)
    if duration_max is not None and dma is None:
        return None, "Parameter 'durationMax' must be an integer."
    if dma is not None:
        body["durationMax"] = dma

    # --- bond boolean flags ---
    es = _canon_bool(exclude_subordinated)
    if exclude_subordinated is not None and es is None:
        return None, "Parameter 'excludeSubordinated' must be boolean (true/false)."
    if es is not None:
        body["excludeSubordinated"] = es

    ep = _canon_bool(exclude_perpetuals)
    if exclude_perpetuals is not None and ep is None:
        return None, "Parameter 'excludePerpetuals' must be boolean (true/false)."
    if ep is not None:
        body["excludePerpetuals"] = ep

    # --- orderBy ---
    if order_by is not None:
        s = str(order_by).strip()
        if s:
            body["orderBy"] = s

    if not body:
        return None, (
            "At least one filter must be provided in the request body "
            "(e.g., regions, sectors, currency, or any *Min/*Max field)."
        )

    return body, None


async def _run_explore_bond(
    skip: int | None,
    take: int | None,
    body: dict[str, Any],
    api_token: str | None,
) -> str:
    url = f"{EODHD_API_BASE}/mp/praams/explore/bond?1=1"
    if skip is not None:
        url += f"&skip={int(skip)}"
    if take is not None:
        url += f"&take={int(take)}"
    if api_token:
        url += f"&api_token={api_token}"

    data = await make_request(
        url,
        method="POST",
        json_body=body,
        headers={"Content-Type": "application/json"},
    )

    if data is None:
        raise ToolError("No response from API.")

    if isinstance(data, dict) and data.get("error"):
        raise ToolError(str(data["error"]))
    try:
        return json.dumps(data, indent=2)
    except Exception:
        raise ToolError("Unexpected JSON response format from API.")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_praams_smart_screener_bond(
        # pagination
        skip: int | None = 0,
        take: int | None = 50,
        # geography / classification
        regions: list[int] | None = None,
        countries: list[int] | None = None,
        sectors: list[int] | None = None,
        industries: list[int] | None = None,
        capitalisation: list[int] | None = None,
        currency: list[str] | None = None,
        # ratio / return factors (1..7)
        mainRatioMin: int | None = None,
        mainRatioMax: int | None = None,
        valuationMin: int | None = None,
        valuationMax: int | None = None,
        performanceMin: int | None = None,
        performanceMax: int | None = None,
        profitabilityMin: int | None = None,
        profitabilityMax: int | None = None,
        growthMomMin: int | None = None,
        growthMomMax: int | None = None,
        otherMin: int | None = None,
        otherMax: int | None = None,
        analystViewMin: int | None = None,
        analystViewMax: int | None = None,
        dividendsMin: int | None = None,
        dividendsMax: int | None = None,
        marketViewMin: int | None = None,
        marketViewMax: int | None = None,
        couponsMin: int | None = None,
        couponsMax: int | None = None,
        # risk factors (1..7)
        countryRiskMin: int | None = None,
        countryRiskMax: int | None = None,
        liquidityMin: int | None = None,
        liquidityMax: int | None = None,
        stressTestMin: int | None = None,
        stressTestMax: int | None = None,
        volatilityMin: int | None = None,
        volatilityMax: int | None = None,
        solvencyMin: int | None = None,
        solvencyMax: int | None = None,
        # bond numeric filters (Int32?)
        yieldMin: int | None = None,
        yieldMax: int | None = None,
        durationMin: int | None = None,
        durationMax: int | None = None,
        # bond flags
        excludeSubordinated: bool | None = None,
        excludePerpetuals: bool | None = None,
        # sorting
        orderBy: str | None = None,
        # auth
        api_token: str | None = None,
    ) -> str:
        """

        [PRAAMS] Screen and filter bonds using multi-factor risk-return criteria.
        Filter by region, country, sector, currency, yield range, duration range, PRAAMS score ranges (1-7),
        and exclude subordinated or perpetual bonds. Returns paginated matching bonds with scores.
        Consumes 10 API calls per request.
        For equity screening, use get_mp_praams_smart_screener_equity.
        For deep analysis of a single bond, use get_mp_praams_bond_analyze_by_isin.
        If you only have a company name or ticker, call resolve_ticker first to obtain the ISIN.


        Returns:
          JSON object with Praams envelope:
            - item (object):
                - peers (array): matching bond instruments, each containing:
                    - isin (str): bond ISIN
                    - name (str): bond/issuer name
                    - praamsRatio (float): overall PRAAMS score
                    - totalReturnScore (int): return score (1-7)
                    - totalRiskScore (int): risk score (1-7)
                    - yield (float|null): current yield
                    - duration (float|null): effective duration
                    - couponRate (float|null): coupon rate
                    - maturityDate (str|null): maturity date
                    - currency (str): bond currency
                    - country (str): issuer country
                    - sector (str): issuer sector
                - totalCount (int): total matching instruments (for pagination)
            - success (bool): whether the request succeeded
            - message (str): status message
            - errors (array): list of error messages, empty on success

        Notes:
          - All *Min/*Max fields are 1..7 scale integers (nullable).
          - Bond-specific: yieldMin/Max, durationMin/Max, excludeSubordinated, excludePerpetuals.
          - Provide at least one filter value in the JSON body.

        Examples:
            "High-yield EUR bonds low risk" → currency=["EUR"], yieldMin=5, countryRiskMax=3
            "US investment-grade bonds short duration" → regions=[1], durationMax=3, solvencyMin=5


        """
        st_err = _validate_skip_take(skip, take)
        if st_err:
            raise ToolError(st_err)

        body, b_err = _build_body(
            main_ratio_min=mainRatioMin,
            main_ratio_max=mainRatioMax,
            valuation_min=valuationMin,
            valuation_max=valuationMax,
            performance_min=performanceMin,
            performance_max=performanceMax,
            profitability_min=profitabilityMin,
            profitability_max=profitabilityMax,
            growth_mom_min=growthMomMin,
            growth_mom_max=growthMomMax,
            other_min=otherMin,
            other_max=otherMax,
            analyst_view_min=analystViewMin,
            analyst_view_max=analystViewMax,
            dividends_min=dividendsMin,
            dividends_max=dividendsMax,
            market_view_min=marketViewMin,
            market_view_max=marketViewMax,
            coupons_min=couponsMin,
            coupons_max=couponsMax,
            country_risk_min=countryRiskMin,
            country_risk_max=countryRiskMax,
            liquidity_min=liquidityMin,
            liquidity_max=liquidityMax,
            stress_test_min=stressTestMin,
            stress_test_max=stressTestMax,
            volatility_min=volatilityMin,
            volatility_max=volatilityMax,
            solvency_min=solvencyMin,
            solvency_max=solvencyMax,
            regions=regions,
            countries=countries,
            sectors=sectors,
            industries=industries,
            capitalisation=capitalisation,
            currency=currency,
            yield_min=yieldMin,
            yield_max=yieldMax,
            duration_min=durationMin,
            duration_max=durationMax,
            exclude_subordinated=excludeSubordinated,
            exclude_perpetuals=excludePerpetuals,
            order_by=orderBy,
        )
        if b_err:
            raise ToolError(b_err)
        assert body is not None

        return await _run_explore_bond(skip=skip, take=take, body=body, api_token=api_token)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_praams_smart_screener_bond(
        skip: int | None = 0,
        take: int | None = 50,
        regions: list[int] | None = None,
        sectors: list[int] | None = None,
        currency: list[str] | None = None,
        marketViewMin: int | None = None,
        marketViewMax: int | None = None,
        growthMomMin: int | None = None,
        growthMomMax: int | None = None,
        yieldMin: int | None = None,
        yieldMax: int | None = None,
        durationMin: int | None = None,
        durationMax: int | None = None,
        excludeSubordinated: bool | None = None,
        excludePerpetuals: bool | None = None,
        api_token: str | None = None,
    ) -> str:
        """
        [PRAAMS] Convenience alias for bond screening with common filters.
        Screen bonds by region, sector, currency, yield, duration, and growth/market-view scores.
        For full filter set, use get_mp_praams_smart_screener_bond.
        """
        st_err = _validate_skip_take(skip, take)
        if st_err:
            raise ToolError(st_err)

        body, b_err = _build_body(
            regions=regions,
            sectors=sectors,
            currency=currency,
            market_view_min=marketViewMin,
            market_view_max=marketViewMax,
            growth_mom_min=growthMomMin,
            growth_mom_max=growthMomMax,
            yield_min=yieldMin,
            yield_max=yieldMax,
            duration_min=durationMin,
            duration_max=durationMax,
            exclude_subordinated=excludeSubordinated,
            exclude_perpetuals=excludePerpetuals,
        )
        if b_err:
            raise ToolError(b_err)
        assert body is not None

        return await _run_explore_bond(skip=skip, take=take, body=body, api_token=api_token)
