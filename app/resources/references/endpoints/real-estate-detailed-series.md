# Real Estate Data API — Detailed Series Catalogue

Status: complete
Source: financial-apis (Real Estate Data API)
Docs: https://eodhd.com/financial-apis/real-estate-data-api
Provider: EODHD (BIS residential property prices)
Base URL: https://eodhd.com/api
Path: /real-estate/{code}/detailed/series
Method: GET
Auth: api_token (query)

## Purpose

Lists the catalogue of Detailed Property Prices (DPP) series available for a country — the
exact covered-area, property-type, and vintage combinations that can be requested from
`/real-estate/{code}/detailed`. This is a parameterless catalogue endpoint. Available in the
All-in-One and Fundamentals plans.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| code (path) | Yes | string | ISO alpha-2 country code, case-insensitive (e.g. `US`) |
| api_token | Yes | string | Your API key |

Note: this endpoint always returns JSON — `fmt=csv` is not honoured.

## Response (shape)

```json
{
  "data": [
    {
      "covered_area": "0",
      "covered_area_label": "Whole country",
      "property_type": "1",
      "property_type_label": "All types of dwellings",
      "vintage": "0",
      "vintage_label": "All",
      "compiling_org": "Central bank",
      "priced_unit": "Per dwelling",
      "seasonal_adj": "Not seasonally adjusted",
      "unit_measure": "IX",
      "unit_measure_label": "Index",
      "title": "Whole country, all types of dwellings, all vintages"
    }
  ],
  "meta": {
    "country_code": "US",
    "total": 12
  }
}
```

### Output Format

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| data | array | Array of available DPP series descriptors |
| meta | object | `{ country_code, total }` |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| covered_area | string | Covered-area dimension code |
| covered_area_label | string | Human-readable covered area |
| property_type | string | Property type code |
| property_type_label | string | Human-readable property type |
| vintage | string | Vintage code |
| vintage_label | string | Human-readable vintage |
| compiling_org | string | Compiling organisation |
| priced_unit | string | Priced unit |
| seasonal_adj | string | Seasonal adjustment status |
| unit_measure | string | Unit-of-measure code |
| unit_measure_label | string | Human-readable unit of measure |
| title | string | Human-readable series title |

## Example Requests

```bash
# Catalogue of detailed series for the US
curl "https://eodhd.com/api/real-estate/US/detailed/series?api_token=YOUR_TOKEN"
```

## Notes

- Country codes are ISO alpha-2 and case-insensitive (normalised to uppercase).
- Parameterless catalogue — always returns JSON regardless of `fmt`.
- Unknown country code → 404 (`Symbol not found`).
- API call consumption: 5 calls per request.

## HTTP Status Codes

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| **200** | OK | Request succeeded. Data returned successfully. |
| **402** | Payment Required | API limit used up. Upgrade plan or wait for limit reset. |
| **403** | Unauthorized | Invalid API key. Check your `api_token` parameter. |
| **404** | Not Found | Unknown country code (`Symbol not found`). |
| **429** | Too Many Requests | Exceeded rate limit (requests per minute). Slow down requests. |

### Error Response Format

```json
{
  "error": "Error message description",
  "code": 404
}
```
