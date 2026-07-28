# Interest Rates API — Reference Rates

Status: complete
Source: financial-apis (Interest Rates API — SOFR, Fed Funds, ECB, BoE)
Docs: https://eodhd.com/financial-apis/interest-rates-api-sofr-fed-funds-ecb-boe-policy-rates
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /rates/reference-rates
Method: GET
Auth: api_token (query)

## Purpose

Provides daily benchmark / reference interest-rate time series — overnight and term rates such as SOFR, EFFR, OBFR, ESTR, SONIA, plus the SOFR averages and compounded index. Includes NY Fed percentiles and traded volume where the source publishes them. Used for floating-rate discounting, funding analysis, and derivatives pricing. Returns the standard JSON envelope `{data, meta, links}` and is paginated.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key |
| filter[code] | No | string | Rate code(s), comma-separated. USD overnight: `SOFR`, `EFFR`, `OBFR`, `TGCR`, `BGCR`; SOFR averages / index: `SOFR30D`, `SOFR90D`, `SOFR180D`, `SOFRINDEX`; GBP: `SONIA`; EUR: `ESTR` |
| filter[currency] | No | string | Currency: `USD`, `GBP`, or `EUR` (comma-separated list allowed) |
| filter[from] | No | string (YYYY-MM-DD) | Start date |
| filter[to] | No | string (YYYY-MM-DD) | End date |
| page[limit] | No | integer | Records per page (default 20, max 100) |
| page[offset] | No | integer | Zero-based pagination offset |

## Response (shape)

```json
{
  "data": [
    {
      "date": "2026-07-24",
      "code": "SOFR",
      "currency": "USD",
      "rate_type": "overnight",
      "rate": 3.64,
      "source": "NY_FED",
      "source_series_id": "secured/sofr",
      "percentiles": { "p1": 3.59, "p25": 3.62, "p75": 3.69, "p99": 3.72 },
      "volume_billion_usd": 2979
    }
  ],
  "meta": {
    "total": 2075,
    "page": { "offset": 0, "limit": 20 }
  },
  "links": {
    "next": "https://eodhd.com/api/rates/reference-rates?filter%5Bcode%5D=SOFR&page%5Boffset%5D=20&page%5Blimit%5D=20"
  }
}
```

### Output Format

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| data | array | Array of reference-rate records |
| meta | object | Metadata: total count and pagination |
| links | object | Pagination links (next page URL or null) |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| date | string (YYYY-MM-DD) | Observation date |
| code | string | Reference rate code |
| currency | string | Currency |
| rate_type | string | `overnight`, `average`, or `index` |
| rate | number | Rate value (percent) |
| source | string | Data provider |
| source_series_id | string | Upstream series identifier |
| percentiles | object or null | `{p1, p25, p75, p99}` distribution (NY Fed rates only) |
| volume_billion_usd | number or null | Traded volume in USD billions (NY Fed rates only) |
| revision_flag | string or null | Upstream revision marker |

## Example Requests

```bash
# SOFR history
curl "https://eodhd.com/api/rates/reference-rates?api_token=YOUR_TOKEN&filter%5Bcode%5D=SOFR"

# EUR reference rates from a start date
curl "https://eodhd.com/api/rates/reference-rates?api_token=YOUR_TOKEN&filter%5Bcurrency%5D=EUR&filter%5Bfrom%5D=2025-01-01"

# Using the helper client
python eodhd_client.py --endpoint rates/reference-rates --filter-param code=SOFR --filter-param from=2025-01-01
```

## Notes

- Filters use JSON:API bracket syntax: `filter[code]`, `filter[currency]`, `filter[from]`, `filter[to]`.
- `filter[code]` and `filter[currency]` each accept a comma-separated list to fetch several series at once.
- `percentiles` and `volume_billion_usd` are populated for NY Fed rates only; other codes return them as null.
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
