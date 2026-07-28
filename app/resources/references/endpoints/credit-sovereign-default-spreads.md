# Credit & Sovereign Risk API — Rating-based Default Spreads

Status: complete
Source: financial-apis (Credit & Sovereign Risk Data API)
Docs: https://eodhd.com/financial-apis/credit-sovereign-risk-data-api
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /credit-risk/sovereign/default-spreads
Method: GET
Auth: api_token (query)

## Purpose

Provides the default spread for each credit-rating bucket — a lookup table mapping a rating (e.g. `Aaa`, `Baa2`) to a default spread. Used to derive a cost-of-debt or country/company risk premium from a rating. Returns the standard JSON envelope `{data, meta, links}` and is paginated.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key |
| filter[rating] | No | string | Rating bucket (Moody's-style scale, e.g. `Aaa`, `Baa2`) |
| filter[as_of] | No | string (YYYY-MM-DD) | As-of date; defaults to the latest snapshot |
| page[limit] | No | integer | Records per page (default 20, max 100) |
| page[offset] | No | integer | Zero-based pagination offset |

## Response (shape)

```json
{
  "data": [
    {
      "rating": "A1",
      "as_of_date": "2026-01-01T00:00:00+00:00",
      "default_spread": 0.005993,
      "source": "damodaran"
    }
  ],
  "meta": {
    "total": 20,
    "page": { "offset": 0, "limit": 20 },
    "dataset": "rating_default_spread",
    "source": "damodaran",
    "frequency": "annual",
    "attribution": "Damodaran, NYU Stern (annual). Rating-to-default-spread lookup table; values normalised from basis points to fractions (e.g. 60bp -> 0.006)."
  },
  "links": { "next": null }
}
```

### Output Format

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| data | array | Array of rating default-spread records |
| meta | object | Metadata: total count, pagination, dataset, source, frequency, attribution |
| links | object | Pagination links (next page URL or null) |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| rating | string | Rating bucket (Moody's-style scale) |
| as_of_date | string (ISO 8601) | Snapshot date (e.g. 2026-01-01T00:00:00+00:00) |
| default_spread | number | Default spread for the rating (fraction; 0.005993 ≈ 60 bps) |
| source | string | Data provider |

## Example Requests

```bash
# Default spread for the Baa2 rating bucket
curl "https://eodhd.com/api/credit-risk/sovereign/default-spreads?api_token=YOUR_TOKEN&filter%5Brating%5D=Baa2"

# Rating default spreads as of a specific date
curl "https://eodhd.com/api/credit-risk/sovereign/default-spreads?api_token=YOUR_TOKEN&filter%5Bas_of%5D=2025-01-01"

# Using the helper client
python eodhd_client.py --endpoint credit-risk/sovereign/default-spreads --filter-param rating=Baa2
```

## Notes

- Filters use JSON:API bracket syntax: `filter[rating]`, `filter[as_of]`.
- `default_spread` is returned as a fraction (0.005993 ≈ 60 bps).
- This is the rating-to-spread mapping used to derive country risk premiums.
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
