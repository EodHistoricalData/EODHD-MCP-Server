# Credit & Sovereign Risk API — CDS Market Aggregates

Status: complete
Source: financial-apis (Credit & Sovereign Risk Data API)
Docs: https://eodhd.com/financial-apis/credit-sovereign-risk-data-api
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /credit-risk/cds-market/aggregates
Method: GET
Auth: api_token (query)

## Purpose

Provides aggregated CDS (credit default swap) market statistics — e.g. gross notional outstanding — broken down by a chosen dimension such as credit grade or cleared status. Used to monitor structural CDS-market size, composition, and activity over time. Returns the standard JSON envelope `{data, meta, links}` and is paginated.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key |
| filter[metric] | No | string | Metric to aggregate. Currently `gross_notional` |
| filter[dimension] | No | string | Breakdown dimension: `grade` or `cleared_status` |
| filter[value] | No | string | Value within the chosen dimension (e.g. a specific grade) |
| filter[region] | No | string | Region scope (e.g. `Europe`, `Asia`) |
| filter[from] | No | string (YYYY-MM-DD) | Start date |
| filter[to] | No | string (YYYY-MM-DD) | End date |
| page[limit] | No | integer | Records per page (default 20, max 100) |
| page[offset] | No | integer | Zero-based pagination offset |

## Response (shape)

```json
{
  "data": [
    {
      "as_of_date": "2026-07-03T00:00:00+00:00",
      "release_date": "2026-07-20T00:00:00+00:00",
      "metric": "gross_notional",
      "breakdown_dimension": "grade",
      "breakdown_value": "HY",
      "region": "Europe",
      "usd_notional_mn": 585455,
      "source": "cftc"
    }
  ],
  "meta": {
    "total": 75,
    "page": { "offset": 0, "limit": 20 },
    "dataset": "cds_market_aggregates",
    "source": "cftc",
    "frequency": "weekly",
    "units": "millions USD",
    "attribution": "Source: CFTC Weekly Swaps Report (public domain). Values in millions USD."
  },
  "links": {
    "next": "https://eodhd.com/api/credit-risk/cds-market/aggregates?page%5Boffset%5D=20&page%5Blimit%5D=20"
  }
}
```

### Output Format

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| data | array | Array of CDS market aggregate records |
| meta | object | Metadata: total count, pagination, dataset, source, frequency, units, attribution |
| links | object | Pagination links (next page URL or null) |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| as_of_date | string (ISO 8601) | Observation date (e.g. 2026-07-03T00:00:00+00:00) |
| release_date | string (ISO 8601) or null | Data release date |
| metric | string | Metric name (e.g. `gross_notional`) |
| breakdown_dimension | string | Dimension used for the breakdown (`grade`, `cleared_status`) |
| breakdown_value | string | Value within the dimension |
| region | string | Region scope |
| usd_notional_mn | number | Notional in USD millions |
| source | string | Data provider |

## Example Requests

```bash
# Gross notional by credit grade over a window
curl "https://eodhd.com/api/credit-risk/cds-market/aggregates?api_token=YOUR_TOKEN&filter%5Bmetric%5D=gross_notional&filter%5Bdimension%5D=grade&filter%5Bfrom%5D=2026-01-01&filter%5Bto%5D=2026-06-01"

# Notional by cleared status
curl "https://eodhd.com/api/credit-risk/cds-market/aggregates?api_token=YOUR_TOKEN&filter%5Bdimension%5D=cleared_status"

# Using the helper client
python eodhd_client.py --endpoint credit-risk/cds-market/aggregates --filter-param metric=gross_notional --filter-param dimension=grade
```

## Notes

- Filters use JSON:API bracket syntax: `filter[metric]`, `filter[dimension]`, `filter[value]`, `filter[region]`, `filter[from]`, `filter[to]`.
- `filter[metric]` currently supports only `gross_notional`.
- `filter[dimension]` supports `grade` and `cleared_status`; `filter[value]` selects a value within that dimension.
- Notional is reported in USD millions (`usd_notional_mn`).
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
