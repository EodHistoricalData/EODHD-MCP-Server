# ETF Held By API (funds holding a security)

Status: beta
Source: financial-apis (ETF Holdings API)
Docs: https://eodhd.com/financial-apis/etf-holdings-api
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /etf/security/{ticker}/held-by
Method: GET
Auth: api_token (query)

## Purpose

Reverse lookup: lists the US-listed ETFs that hold a given security, sorted by the weight of the security in
each fund. Positions come from the funds' latest SEC N-PORT filings. Beta: field names and coverage can change.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key for authentication |
| ticker (path) | Yes | string | The security that is looked up, not a fund. US tickers (`NVDA`, `XOM`) and foreign tickers with an exchange suffix (`ASML.AS`) are accepted. |
| page[offset] | No | integer | Pagination offset, zero-based (default 0) |
| page[limit] | No | integer | Funds per page, 1 to 5000 (default 100). Values outside the range return 422. |

There is no `fmt` parameter.

## Cost and plans

10 API calls per request. Available on the Fundamentals Data Feed and All-In-One plans. The demo token is
rejected here with 403.

## Response (shape)

```json
{
  "data": {
    "security": { "ticker": "NVDA", "exchange": "US", "name": "NVIDIA Corp" },
    "held_by_count": 0,
    "funds": [
      { "ticker": "XLK", "name": "...", "weight": 0, "shares": 0, "value_usd": 0, "report_date": "YYYY-MM-DD" }
    ]
  },
  "meta": { "total": 0, "offset": 0, "limit": 100 },
  "links": { "next": "/api/etf/security/NVDA/held-by?page[offset]=100&page[limit]=100" }
}
```

- `funds` is sorted by `weight` descending.
- `links.next` is a relative URL without the token; add `api_token` yourself. It is null on the last page.
- A request past the end returns an empty `funds` list.

## Errors

- 401: plain text `Unauthenticated`.
- 403: plain text; the plan does not include the API, or the demo token was used.
- 404 JSON: an unknown ticker returns 404 without a `code`.
- 422 JSON: `{"errors":{"page.limit":["The page.limit may not be greater than 5000."]}}`.
- 429: rate limit of the plan.

## Example

```
https://eodhd.com/api/etf/security/NVDA/held-by?api_token=YOUR_TOKEN&page[offset]=0&page[limit]=100
```

## Related

- ETF Holdings (`/etf/holdings/{ticker}`): positions of one fund.
