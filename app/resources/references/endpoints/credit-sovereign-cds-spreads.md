# Credit & Sovereign Risk API — Sovereign CDS Spreads

Status: complete
Source: financial-apis (Credit & Sovereign Risk Data API)
Docs: https://eodhd.com/financial-apis/credit-sovereign-risk-data-api
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /credit-risk/sovereign/cds-spreads
Method: GET
Auth: api_token (query)

## Purpose

Provides sovereign credit default swap (CDS) spreads per country, including the raw CDS spread and the spread net of the Switzerland (near-riskless) benchmark, with Moody's rating context. Used for sovereign-risk pricing, default-probability estimation, and relative-value analysis. Returns the standard JSON envelope `{data, meta, links}` and is paginated.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key |
| filter[country] | No | string | ISO 3166-1 alpha-3 code, or a comma-separated list (e.g. `USA`, `DEU`, `FRA`). Full country names are NOT matched |
| filter[as_of] | No | string (YYYY-MM-DD) | As-of date; defaults to the latest snapshot |
| page[limit] | No | integer | Records per page (default 20, max 100) |
| page[offset] | No | integer | Zero-based pagination offset |

## Response (shape)

```json
{
  "data": [
    {
      "country_iso3": "FRA",
      "country_name": "France",
      "as_of_date": "2026-01-01T00:00:00+00:00",
      "moodys_rating": "Aa3",
      "cds_spread": 0.0064,
      "cds_spread_net_of_switzerland": 0.005,
      "source": "damodaran"
    }
  ],
  "meta": {
    "total": 90,
    "page": { "offset": 0, "limit": 20 },
    "dataset": "sovereign_cds_spread",
    "source": "damodaran",
    "frequency": "annual",
    "attribution": "Damodaran, NYU Stern (annual). Sovereign 10Y CDS spreads where the market is liquid; NULL where no liquid market."
  },
  "links": { "next": null }
}
```

### Output Format

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| data | array | Array of sovereign CDS spread records |
| meta | object | Metadata: total count, pagination, dataset, source, frequency, attribution |
| links | object | Pagination links (next page URL or null) |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| country_iso3 | string | ISO 3166-1 alpha-3 country code |
| country_name | string | Country name |
| as_of_date | string (ISO 8601) | Snapshot date (e.g. 2026-01-01T00:00:00+00:00) |
| moodys_rating | string or null | Moody's sovereign rating |
| cds_spread | number or null | Sovereign CDS spread (fraction; 0.0064 = 64 bps) |
| cds_spread_net_of_switzerland | number or null | CDS spread net of the Switzerland benchmark (fraction) |
| source | string | Data provider |

## Example Requests

```bash
# Latest sovereign CDS spread for France
curl "https://eodhd.com/api/credit-risk/sovereign/cds-spreads?api_token=YOUR_TOKEN&filter%5Bcountry%5D=FRA"

# Spreads as of a specific date
curl "https://eodhd.com/api/credit-risk/sovereign/cds-spreads?api_token=YOUR_TOKEN&filter%5Bas_of%5D=2025-06-30"

# Using the helper client
python eodhd_client.py --endpoint credit-risk/sovereign/cds-spreads --filter-param country=FRA
```

## Notes

- Filters use JSON:API bracket syntax: `filter[country]`, `filter[as_of]`.
- `filter[country]` matches ISO 3166-1 alpha-3 codes only (comma-separated list allowed); full country names are not matched.
- Spreads are returned as fractions (0.0064 = 64 bps).
- Pagination uses `page[limit]` (default 20, max 100) and `page[offset]`.

## HTTP Status Codes

The API returns standard HTTP status codes to indicate success or failure:

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| **200** | OK | Request succeeded. Data returned successfully. |
| **402** | Payment Required | API limit used up, or your plan lacks endpoint access. |
| **403** | Forbidden | Invalid API key or plan lacks endpoint access. Check your `api_token`. |
| **422** | Unprocessable Entity | Validation error (e.g. bad filter or pagination parameter). |
| **429** | Too Many Requests | Exceeded rate limit (requests per minute). Slow down requests. |

### Error Response Format

When an error occurs, the API returns a JSON response with error details:

```json
{
  "error": "Error message description",
  "code": 403
}
```

### Handling Errors

**Python Example**:
```python
import requests

def make_api_request(url, params):
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raises HTTPError for bad status codes
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 402:
            print("Error: API limit exceeded. Please upgrade your plan.")
        elif e.response.status_code == 403:
            print("Error: Invalid API key. Check your credentials.")
        elif e.response.status_code == 429:
            print("Error: Rate limit exceeded. Please slow down your requests.")
        else:
            print(f"HTTP Error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
```

**Best Practices**:
- Always check status codes before processing response data
- Implement exponential backoff for 429 errors
- Cache responses to reduce API calls
- Monitor your API usage in the user dashboard
