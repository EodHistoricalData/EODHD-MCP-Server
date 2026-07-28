# Real Estate Data API — Selected Property Prices (SPP)

Status: complete
Source: financial-apis (Real Estate Data API)
Docs: https://eodhd.com/financial-apis/real-estate-data-api
Provider: EODHD (BIS residential property prices)
Base URL: https://eodhd.com/api
Path: /real-estate/{code}
Method: GET
Auth: api_token (query)

## Purpose

Returns Selected Property Prices (SPP) for a country — the headline harmonised residential
property price series from the BIS. Values can be nominal or real, expressed as an index or
year-on-year change. For granular breakdowns use `/real-estate/{code}/detailed`. Available in
the All-in-One and Fundamentals plans.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| code (path) | Yes | string | ISO alpha-2 country code, case-insensitive (e.g. `US`) |
| api_token | Yes | string | Your API key |
| filter[type] | No | string | `nominal` or `real` |
| filter[metric] | No | string | `index` or `yoy` |
| filter[from] | No | string | Start period `YYYY-Qn` (e.g. `2020-Q1`) |
| filter[to] | No | string | End period `YYYY-Qn` |
| sort | No | string | `period`, `-period`, `value`, or `-value` |
| fmt | No | string | `json` (default) or `csv` |
| page[limit] | No | integer | Records per page, 1–500 (default 50). Above 500 → 422 |
| page[offset] | No | integer | Pagination offset, ≥ 0 (default 0) |

## Response (shape)

```json
{
  "data": [
    {
      "period": "2024-Q1",
      "value": 312.5,
      "type": "real",
      "metric": "index"
    }
  ],
  "meta": {
    "country_code": "US",
    "country_name": "United States",
    "type": "real",
    "metric": "index",
    "base_year": "2010",
    "frequency": "Q",
    "source": "BIS",
    "total": 200,
    "from": "1970-Q1",
    "to": "2024-Q1",
    "offset": 0,
    "limit": 50
  },
  "links": {
    "next": null
  }
}
```

### Output Format

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| data | array | Array of SPP observation records |
| meta | object | Series metadata + pagination |
| links | object | `{ next }` — next page URL or null |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| period | string | Observation period (e.g. `2024-Q1`) |
| value | number | Price index or year-on-year value |
| type | string | `nominal` or `real` |
| metric | string | `index` or `yoy` |

## Example Requests

```bash
# US real house price index
curl "https://eodhd.com/api/real-estate/US?api_token=YOUR_TOKEN&filter[type]=real&filter[metric]=index"

# UK nominal YoY since 2020
curl "https://eodhd.com/api/real-estate/GB?api_token=YOUR_TOKEN&filter[type]=nominal&filter[metric]=yoy&filter[from]=2020-Q1"
```

## Notes

- Country codes are ISO alpha-2 and case-insensitive (normalised to uppercase).
- Unknown country code → 404 (`Symbol not found`). Unknown filter key → 422.
- API call consumption: 5 calls per request.

## HTTP Status Codes

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| **200** | OK | Request succeeded. Data returned successfully. |
| **402** | Payment Required | API limit used up. Upgrade plan or wait for limit reset. |
| **403** | Unauthorized | Invalid API key. Check your `api_token` parameter. |
| **404** | Not Found | Unknown country code (`Symbol not found`). |
| **422** | Unprocessable Entity | Invalid filter key or `page[limit]` above 500. |
| **429** | Too Many Requests | Exceeded rate limit (requests per minute). Slow down requests. |

### Error Response Format

```json
{
  "error": "Error message description",
  "code": 404
}
```
