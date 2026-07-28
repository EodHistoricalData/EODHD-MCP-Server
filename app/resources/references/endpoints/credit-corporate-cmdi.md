# Credit & Sovereign Risk API — Corporate CMDI

Status: complete
Source: financial-apis (Credit & Sovereign Risk Data API)
Docs: https://eodhd.com/financial-apis/credit-sovereign-risk-data-api
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /credit-risk/corporate/cmdi
Method: GET
Auth: api_token (query)

## Purpose

Provides the Corporate Market-implied Default Index (CMDI) time series — an aggregate market gauge of corporate credit stress with investment-grade (IG) and high-yield (HY) sub-indices. Used to track default risk across the credit cycle. Higher CMDI values indicate greater implied default risk. Returns the standard JSON envelope `{data, meta, links}` and is paginated.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key |
| filter[from] | No | string (YYYY-MM-DD) | Start date |
| filter[to] | No | string (YYYY-MM-DD) | End date |
| page[limit] | No | integer | Records per page (default 20, max 100) |
| page[offset] | No | integer | Zero-based pagination offset |

## Response (shape)

```json
{
  "data": [
    {
      "as_of_date": "2026-06-19T00:00:00+00:00",
      "market_cmdi": 0.13,
      "ig_cmdi": 0.23,
      "hy_cmdi": 0.06,
      "source": "ny_fed"
    }
  ],
  "meta": {
    "total": 1120,
    "page": { "offset": 0, "limit": 20 },
    "dataset": "corporate_bond_market_distress_index",
    "source": "ny_fed",
    "frequency": "weekly",
    "attribution": "© Federal Reserve Bank of New York. Content subject to the Terms of Use at newyorkfed.org."
  },
  "links": {
    "next": "https://eodhd.com/api/credit-risk/corporate/cmdi?page%5Boffset%5D=20&page%5Blimit%5D=20"
  }
}
```

### Output Format

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| data | array | Array of CMDI records |
| meta | object | Metadata: total count, pagination, dataset, source, frequency, attribution |
| links | object | Pagination links (next page URL or null) |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| as_of_date | string (ISO 8601) | Observation date (e.g. 2026-06-19T00:00:00+00:00) |
| market_cmdi | number or null | Aggregate market CMDI |
| ig_cmdi | number or null | Investment-grade sub-index |
| hy_cmdi | number or null | High-yield sub-index |
| source | string | Data provider |

## Example Requests

```bash
# CMDI time series for a date window
curl "https://eodhd.com/api/credit-risk/corporate/cmdi?api_token=YOUR_TOKEN&filter%5Bfrom%5D=2026-01-01&filter%5Bto%5D=2026-06-01"

# Latest CMDI
curl "https://eodhd.com/api/credit-risk/corporate/cmdi?api_token=YOUR_TOKEN"

# Using the helper client
python eodhd_client.py --endpoint credit-risk/corporate/cmdi --filter-param from=2026-01-01 --filter-param to=2026-06-01
```

## Notes

- Filters use JSON:API bracket syntax: `filter[from]`, `filter[to]`.
- Time series is keyed on `as_of_date`; higher CMDI values indicate greater implied default risk.
- The series carries the aggregate `market_cmdi` alongside `ig_cmdi` and `hy_cmdi` sub-indices.
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
