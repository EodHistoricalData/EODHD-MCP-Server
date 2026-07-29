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
| code (path) | Yes | string | Country code, case-insensitive: ISO alpha-2 (e.g. `US`) or a BIS aggregate (e.g. `4T`) |
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
      "compiling_org": "2",
      "priced_unit": "0",
      "seasonal_adj": "1",
      "unit_measure": "519: Index, 2005 = 100",
      "unit_measure_label": null,
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
| links | object | Pagination links (`next`), null when there is no further page |
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
| compiling_org | string | BIS compiling-organisation code, e.g. `2` — not a label |
| priced_unit | string | BIS priced-unit code, e.g. `0` — not a label |
| seasonal_adj | string | BIS seasonal-adjustment code, e.g. `1` — not a label |
| unit_measure | string | Unit of measure as returned by BIS, e.g. `519: Index, 2005 = 100` |
| unit_measure_label | string \| null | Extra label; currently null for every series |
| title | string | Human-readable series title |

## Example Requests

```bash
# Catalogue of detailed series for the US
curl "https://eodhd.com/api/real-estate/US/detailed/series?api_token=YOUR_TOKEN"
```

## Notes

- Country codes are case-insensitive (normalised to uppercase). Most are ISO alpha-2; the dataset
  also carries BIS aggregates such as `4T` (emerging markets) and `5R`.
- Parameterless catalogue — always returns JSON regardless of `fmt`.
- Unknown country code → 404 (`Symbol not found`).
- API call consumption: 5 calls per request.

## HTTP Status Codes

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| **200** | OK | Request succeeded. Data returned successfully. |
| **402** | Payment Required | API limit used up. Upgrade plan or wait for limit reset. |
| **401** | Unauthorized | Missing or invalid credentials. Check your `api_token` / OAuth connection. |
| **403** | Forbidden | The account's plan does not include this dataset. |
| **404** | Not Found | Unknown country code (`Symbol not found`). |
| **429** | Too Many Requests | Exceeded rate limit (requests per minute). Slow down requests. |

### Error Response Format

```json
{
  "error": "Error message description",
  "code": 404
}
```
