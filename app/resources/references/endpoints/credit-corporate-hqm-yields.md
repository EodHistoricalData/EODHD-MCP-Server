# Credit & Sovereign Risk API — Corporate HQM Yields

Status: complete
Source: financial-apis (Credit & Sovereign Risk Data API)
Docs: https://eodhd.com/financial-apis/credit-sovereign-risk-data-api
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /credit-risk/corporate/hqm-yields
Method: GET
Auth: api_token (query)

## Purpose

Provides the High Quality Market (HQM) corporate bond yield curve — par and spot yields by tenor (in years). Used for discounting long-dated liabilities (e.g. pension obligations) and corporate term-structure analysis. Returns the standard JSON envelope `{data, meta, links}` and is paginated.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key |
| filter[tenor] | No | string | Tenor(s) in years, comma-separated. Allowed: 1, 2, 3, 5, 7, 10, 15, 20, 25, 30 |
| filter[type] | No | string | Yield type: `par` or `spot` (comma-separated list allowed) |
| filter[from] | No | string (YYYY-MM-DD) | Start date |
| filter[to] | No | string (YYYY-MM-DD) | End date |
| page[limit] | No | integer | Records per page (default 20, max 100) |
| page[offset] | No | integer | Zero-based pagination offset |

## Response (shape)

```json
{
  "data": [
    {
      "series_id": "HQMCB10YR",
      "tenor_years": 10,
      "yield_type": "spot",
      "as_of_date": "2026-06-01T00:00:00+00:00",
      "yield_value": 5.27,
      "source": "fred"
    }
  ],
  "meta": {
    "total": 510,
    "page": { "offset": 0, "limit": 20 },
    "dataset": "hqm_corporate_yield_curve",
    "source": "fred",
    "frequency": "monthly",
    "attribution": "U.S. Department of the Treasury, HQM Corporate Bond Yield Curve, retrieved from FRED, Federal Reserve Bank of St. Louis (public domain)."
  },
  "links": {
    "next": "https://eodhd.com/api/credit-risk/corporate/hqm-yields?page%5Boffset%5D=20&page%5Blimit%5D=20"
  }
}
```

### Output Format

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| data | array | Array of HQM yield records |
| meta | object | Metadata: total count, pagination, dataset, source, frequency, attribution |
| links | object | Pagination links (next page URL or null) |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| series_id | string | HQM series identifier |
| tenor_years | integer | Tenor in years |
| yield_type | string | `par` or `spot` |
| as_of_date | string (ISO 8601) | Observation date (e.g. 2026-06-01T00:00:00+00:00) |
| yield_value | number | Yield for the tenor (percent) |
| source | string | Data provider |

## Example Requests

```bash
# 10-year HQM spot yield
curl "https://eodhd.com/api/credit-risk/corporate/hqm-yields?api_token=YOUR_TOKEN&filter%5Btenor%5D=10&filter%5Btype%5D=spot"

# Par HQM yields for 2Y, 5Y, 10Y over a window
curl "https://eodhd.com/api/credit-risk/corporate/hqm-yields?api_token=YOUR_TOKEN&filter%5Btenor%5D=2,5,10&filter%5Btype%5D=par&filter%5Bfrom%5D=2026-01-01&filter%5Bto%5D=2026-06-01"

# Using the helper client
python eodhd_client.py --endpoint credit-risk/corporate/hqm-yields --filter-param tenor=2,5,10 --filter-param type=par
```

## Notes

- Filters use JSON:API bracket syntax: `filter[tenor]`, `filter[type]`, `filter[from]`, `filter[to]`.
- `filter[tenor]` accepts a comma-separated list of tenors in years; allowed values are 1, 2, 3, 5, 7, 10, 15, 20, 25, 30.
- `filter[type]` accepts `par` (par yield curve) or `spot` (spot yield curve).
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
