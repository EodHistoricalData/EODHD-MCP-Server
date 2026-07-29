# Real Estate Data API — Countries

Status: complete
Source: financial-apis (Real Estate Data API)
Docs: https://eodhd.com/financial-apis/real-estate-data-api
Provider: EODHD (BIS residential property prices)
Base URL: https://eodhd.com/api
Path: /real-estate/countries
Method: GET
Auth: api_token (query)

## Purpose

Lists the countries covered by the Real Estate Data API and which datasets each country
carries: Selected Property Prices (SPP, headline harmonised series) and Detailed Property
Prices (DPP, granular national series). Use this to discover valid country codes before
querying the other real-estate endpoints. Available in the All-in-One and Fundamentals plans.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key |
| sort | No | string | `code`, `-code`, `name`, or `-name` |
| fmt | No | string | `json` (default) or `csv` |
| page[limit] | No | integer | Records per page, 1–500 (default 50). Above 500 → 422 |
| page[offset] | No | integer | Pagination offset, ≥ 0 (default 0) |

## Response (shape)

```json
{
  "data": [
    {
      "code": "US",
      "name": "United States",
      "has_spp": true,
      "has_dpp": true
    }
  ],
  "meta": {
    "total": 60,
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
| data | array | Array of covered-country records |
| meta | object | `{ total, offset, limit }` |
| links | object | `{ next }` — next page URL or null |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| code | string | ISO alpha-2 country code (e.g. `US`) |
| name | string | Country name |
| has_spp | boolean | Selected Property Prices available |
| has_dpp | boolean | Detailed Property Prices available |

## Example Requests

```bash
# All covered countries (JSON)
curl "https://eodhd.com/api/real-estate/countries?api_token=YOUR_TOKEN&fmt=json"

# Sorted by name, second page of 100
curl "https://eodhd.com/api/real-estate/countries?api_token=YOUR_TOKEN&sort=name&page[limit]=100&page[offset]=100"
```

## Notes

- Country codes are ISO alpha-2 and case-insensitive (normalised to uppercase).
- API call consumption: 5 calls per request.
- Part of the Real Estate Data API (BIS residential property prices).

## HTTP Status Codes

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| **200** | OK | Request succeeded. Data returned successfully. |
| **402** | Payment Required | API limit used up. Upgrade plan or wait for limit reset. |
| **403** | Unauthorized | Invalid API key. Check your `api_token` parameter. |
| **422** | Unprocessable Entity | Invalid filter key or `page[limit]` above 500. |
| **429** | Too Many Requests | Exceeded rate limit (requests per minute). Slow down requests. |

### Error Response Format

```json
{
  "error": "Error message description",
  "code": 403
}
```
