# Real Estate Data API — Detailed Property Prices (DPP)

Status: complete
Source: financial-apis (Real Estate Data API)
Docs: https://eodhd.com/financial-apis/real-estate-data-api
Provider: EODHD (BIS residential property prices)
Base URL: https://eodhd.com/api
Path: /real-estate/{code}/detailed
Method: GET
Auth: api_token (query)

## Purpose

Returns Detailed Property Prices (DPP) for a country — the granular national residential
property price series from the BIS, broken down by covered area, property type, vintage
(new vs existing dwellings), and frequency. For the headline series use `/real-estate/{code}`.
Discover available series combinations with `/real-estate/{code}/detailed/series`. Available in
the All-in-One and Fundamentals plans.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| code (path) | Yes | string | ISO alpha-2 country code, case-insensitive (e.g. `AE`) |
| api_token | Yes | string | Your API key |
| filter[area] | No | string | BIS covered-area dimension code |
| filter[property_type] | No | string | Property type code |
| filter[vintage] | No | string | Vintage code (e.g. new vs existing dwellings) |
| filter[freq] | No | string | `Q`, `A`, `M`, or `H` |
| filter[from] | No | string | Start period following series frequency (e.g. `2020-01` or `2020-Q1`) |
| filter[to] | No | string | End period |
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
      "value": 128.4,
      "frequency": "Q",
      "covered_area": "0",
      "covered_area_label": "Whole country",
      "property_type": "1",
      "property_type_label": "All types of dwellings",
      "vintage": "0",
      "vintage_label": "All",
      "unit_measure": "IX",
      "unit_measure_label": "Index"
    }
  ],
  "meta": {
    "country_code": "AE",
    "source": "BIS",
    "dataset": "DPP",
    "total": 96,
    "offset": 0,
    "limit": 50,
    "filters": {
      "property_type": "1"
    }
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
| data | array | Array of DPP observation records |
| meta | object | `{ country_code, source, dataset, total, offset, limit, filters }` |
| links | object | `{ next }` — next page URL or null |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| period | string | Observation period |
| value | number | Series value |
| frequency | string | Series frequency |
| covered_area | string | Covered-area dimension code |
| covered_area_label | string | Human-readable covered area |
| property_type | string | Property type code |
| property_type_label | string | Human-readable property type |
| vintage | string | Vintage code |
| vintage_label | string | Human-readable vintage |
| unit_measure | string | Unit-of-measure code |
| unit_measure_label | string \| null | Human-readable unit of measure (may be null) |

## Example Requests

```bash
# Detailed UAE prices for property type 1
curl "https://eodhd.com/api/real-estate/AE/detailed?api_token=YOUR_TOKEN&filter[property_type]=1"

# Quarterly detailed US series
curl "https://eodhd.com/api/real-estate/US/detailed?api_token=YOUR_TOKEN&filter[freq]=Q"
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
