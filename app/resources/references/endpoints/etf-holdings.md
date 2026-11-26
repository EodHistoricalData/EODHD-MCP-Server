# ETF Holdings API

Status: beta
Source: financial-apis (ETF Holdings API)
Docs: https://eodhd.com/financial-apis/etf-holdings-api
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /etf/holdings/{ticker}
Method: GET
Auth: api_token (query)

## Purpose

Returns the positions of one US-listed ETF as reported in the fund's SEC N-PORT filing, with weights,
share counts and market values. Asset allocation, sector and region breakdowns and performance figures
are calculated from the same data. Beta: field names and coverage can change. US-listed ETFs only; not
every US ETF is covered yet. Positions come from the latest filing, so they can be several months old.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key for authentication |
| ticker (path) | Yes | string | US ETF ticker, with or without `.US` (`VTI` = `VTI.US`). Other exchanges return 422. |

There is no `fmt` parameter and no pagination: all positions come back in one response. Large funds are
several MB (VTI about 3,500 positions, BND about 5 MB).

## Cost and plans

10 API calls per request (a 404 costs 10 as well). Available on the Fundamentals Data Feed and All-In-One
plans. The demo token works for `VTI`.

## Response (shape)

```json
{
  "data": {
    "General": {
      "Code": "XLE", "Type": "ETF", "Name": "Energy Select Sector SPDR Fund", "Exchange": "US",
      "Issuer": "...", "Fund_Type": "etf", "Net_Assets": 0, "Report_Date": "YYYY-MM-DD",
      "Source": "nport", "Is_Complete": true, "Mapped_Weight_%": 0, "Filed_Positions_Count": 0
    },
    "Holdings": {
      "XOM.US": {
        "Code": "XOM", "Exchange": "US", "Name": "...", "Sector": "Energy", "Industry": "...",
        "Country": "United States", "Country_Code": "US", "Region": "North America",
        "Assets_%": 0, "Shares": 0, "Value_USD": 0, "Contract_Code": null
      }
    },
    "Top_10_Holdings": { "XOM.US": { "...": "same shape as Holdings" } },
    "Holdings_Count": 0,
    "Asset_Allocation": {
      "Cash": { "Long_%": 0, "Short_%": 0, "Net_Assets_%": 0 },
      "Bond": {}, "Stock_US": {}, "Stock_non-US": {}, "Other": {}
    },
    "Sector_Weights": { "Energy": { "Equity_%": 0 } },
    "World_Regions": { "North America": { "Equity_%": 0 } },
    "Performance": {
      "Returns_YTD": 0, "Returns_1Y": 0, "Returns_3Y": 0, "Returns_5Y": 0, "Returns_10Y": 0,
      "1y_Volatility": 0, "3y_Volatility": 0, "3y_SharpRatio": 0
    }
  },
  "meta": [],
  "links": []
}
```

Notes on fields:
- `Holdings` is keyed by `CODE.EXCHANGE` (for example `NVDA.US`, `ASML.AS`). A position without a ticker gets
  another opaque key, possibly with a `~` suffix. Treat keys as opaque.
- `Code`, `Exchange`, `Sector`, `Industry`, `Region` and `Contract_Code` can be null. `Contract_Code`
  identifies an option or other derivative contract.
- `Assets_%` is the weight in percent. It can be negative, and the sum can be above or below 100.
- For a fund with no positions, `Holdings` is an empty list `[]`, not an object.
- `Holdings_Count` is the number of entries in `Holdings`. Lots of one security are summed, so it can be
  below `Filed_Positions_Count`.
- `Mapped_Weight_%` is the share of the fund weight whose positions have a ticker.
- `Sector_Weights` and `World_Regions` cover equities only and can contain an `Unclassified` entry. They are
  empty objects for funds without equities (for example BND).
- `Performance` is an object or null; each value is a number or null.

## Errors

- 401: plain text `Unauthenticated` (missing or invalid token).
- 403: plain text; the plan does not include the API.
- 404 JSON: `{"errors":[{"status":"404","title":"Symbol not found","code":"NOT_COVERED","detail":"..."}]}`.
  Codes: `FUND_NOT_FOUND` (unknown ticker or renamed fund), `NOT_COVERED` (for example gold or bitcoin ETPs,
  ETNs, some small funds), `NO_HOLDINGS_YET` (known fund with no N-PORT filing yet).
- 422 JSON: non-US ticker, for example `{"errors":{"symbol":["ETF data is available for US-listed securities only."]}}`.
- 429: rate limit of the plan.

## Example

```
https://eodhd.com/api/etf/holdings/VTI.US?api_token=YOUR_TOKEN
```

## Related

- ETF Held By (`/etf/security/{ticker}/held-by`): the reverse lookup, funds that hold a security.
