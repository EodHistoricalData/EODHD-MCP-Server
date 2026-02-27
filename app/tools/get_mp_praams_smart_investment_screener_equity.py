# get_mp_praams_smart_investment_screener_equity.py

import json
from typing import Optional, Any, Dict, Tuple

from fastmcp import FastMCP
from app.config import EODHD_API_BASE
from app.api_client import make_request
from mcp.types import ToolAnnotations


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, indent=2)


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _canon_list_ints(v: Any) -> Optional[list[int]]:
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


def _canon_list_strs(v: Any) -> Optional[list[str]]:
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


def _canon_range_1_7(_name: str, v: Any) -> Optional[int]:
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


def _validate_skip_take(skip: Any, take: Any) -> Optional[str]:
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
    currency: Any = None,        # ISO Alpha-3 strings
    # sorting
    order_by: Any = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    body: Dict[str, Any] = {}

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
            return None, "Parameter '{}' must be an integer in [1..7].".format(key)
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

    # --- orderBy ---
    if order_by is not None:
        s = str(order_by).strip()
        if s:
            body["orderBy"] = s

    if not body:
        return None, (
            "At least one filter must be provided in the request body "
            "(e.g., countries, sectors, currency, or any *Min/*Max field)."
        )

    return body, None


async def _run_explore_equity(
    skip: Optional[int],
    take: Optional[int],
    body: Dict[str, Any],
    api_token: Optional[str],
) -> str:
    url = "{}/mp/praams/explore/equity?1=1".format(EODHD_API_BASE)
    if skip is not None:
        url += "&skip={}".format(int(skip))
    if take is not None:
        url += "&take={}".format(int(take))
    if api_token:
        url += "&api_token={}".format(api_token)

    data = await make_request(
        url,
        method="POST",
        json_body=body,
        headers={"Content-Type": "application/json"},
    )

    if data is None:
        return _err("No response from API.")

    try:
        return json.dumps(data, indent=2)
    except Exception:
        return _err("Unexpected JSON response format from API.")


def register(mcp: FastMCP):
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def get_mp_praams_smart_screener_equity(
        # pagination
        skip: Optional[int] = 0,
        take: Optional[int] = 50,
        # geography / classification
        regions: Optional[list[int]] = None,
        countries: Optional[list[int]] = None,
        sectors: Optional[list[int]] = None,
        industries: Optional[list[int]] = None,
        capitalisation: Optional[list[int]] = None,  # 1=small,2=mid,3=large
        currency: Optional[list[str]] = None,        # ISO Alpha-3
        # ratio / return factors (1..7)
        mainRatioMin: Optional[int] = None,
        mainRatioMax: Optional[int] = None,
        valuationMin: Optional[int] = None,
        valuationMax: Optional[int] = None,
        performanceMin: Optional[int] = None,
        performanceMax: Optional[int] = None,
        profitabilityMin: Optional[int] = None,
        profitabilityMax: Optional[int] = None,
        growthMomMin: Optional[int] = None,
        growthMomMax: Optional[int] = None,
        otherMin: Optional[int] = None,
        otherMax: Optional[int] = None,
        analystViewMin: Optional[int] = None,
        analystViewMax: Optional[int] = None,
        dividendsMin: Optional[int] = None,
        dividendsMax: Optional[int] = None,
        # risk factors (1..7)
        countryRiskMin: Optional[int] = None,
        countryRiskMax: Optional[int] = None,
        liquidityMin: Optional[int] = None,
        liquidityMax: Optional[int] = None,
        stressTestMin: Optional[int] = None,
        stressTestMax: Optional[int] = None,
        volatilityMin: Optional[int] = None,
        volatilityMax: Optional[int] = None,
        solvencyMin: Optional[int] = None,
        solvencyMax: Optional[int] = None,
        # sorting
        orderBy: Optional[str] = None,
        # auth
        api_token: Optional[str] = None,
    ) -> str:
        """
        Marketplace: Praams Smart Investment Screener (Equity)
        POST /api/mp/praams/explore/equity?skip={skip}&take={take}

        Matches curl:
          - Query params: skip, take, api_token
          - JSON body: filters (countries/sectors/etc) and ratio bounds.

        Response shape:
          {
            "item": { "peers": [...], "totalCount": N },
            "success": true,
            "message": "",
            "errors": []
          }

        Notes:
          - All *Min/*Max fields are 1..7 scale integers (nullable).
          - Provide at least one filter value in the JSON body.
        """
        st_err = _validate_skip_take(skip, take)
        if st_err:
            return _err(st_err)

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
            order_by=orderBy,
        )
        if b_err:
            return _err(b_err)

        return await _run_explore_equity(skip=skip, take=take, body=body, api_token=api_token)

    # Optional alias (compact, mirrors your curl example)
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    async def mp_praams_smart_screener_equity(
        skip: Optional[int] = 0,
        take: Optional[int] = 50,
        countries: Optional[list[int]] = None,
        sectors: Optional[list[int]] = None,
        dividendsMin: Optional[int] = None,
        dividendsMax: Optional[int] = None,
        solvencyMin: Optional[int] = None,
        solvencyMax: Optional[int] = None,
        api_token: Optional[str] = None,
    ) -> str:
        """
        Convenience alias for the common equity filters shown in docs/examples.
        """
        st_err = _validate_skip_take(skip, take)
        if st_err:
            return _err(st_err)

        body, b_err = _build_body(
            countries=countries,
            sectors=sectors,
            dividends_min=dividendsMin,
            dividends_max=dividendsMax,
            solvency_min=solvencyMin,
            solvency_max=solvencyMax,
        )
        if b_err:
            return _err(b_err)

        return await _run_explore_equity(skip=skip, take=take, body=body, api_token=api_token)
