# Interest Rates API — Central-Bank Policy Rates

Status: complete
Source: financial-apis (Interest Rates API — SOFR, Fed Funds, ECB, BoE)
Docs: https://eodhd.com/financial-apis/interest-rates-api-sofr-fed-funds-ecb-boe-policy-rates
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /rates/policy-rates
Method: GET
Auth: api_token (query)

## Purpose

Provides central-bank policy-rate time series — official target / administered rates set by central banks (e.g. Fed funds target, ECB deposit facility rate, BoE Bank Rate). Used for macro analysis, rate-path tracking, and cross-country policy comparison. Returns the standard JSON envelope `{data, meta, links}` and is paginated.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key |
| filter[code] | No | string | Policy-rate code(s), comma-separated. Values: `FED_TARGET_LOWER`, `FED_TARGET_UPPER`, `ECB_DFR`, `ECB_MRO`, `ECB_MLF`, `BOE_BANK_RATE` |
| filter[country] | No | string | Country / area: `US`, `EU`, or `GB` (comma-separated list allowed) |
| filter[central_bank] | No | string | Central bank: `FED`, `ECB`, or `BOE` (comma-separated list allowed) |
| filter[from] | No | string (YYYY-MM-DD) | Start date |
| filter[to] | No | string (YYYY-MM-DD) | End date |
| page[limit] | No | integer | Records per page (default 20, max 100) |
| page[offset] | No | integer | Zero-based pagination offset |

## Response (shape)

```json
{
  "data": [
    {
      "date": "2026-07-27",
      "code": "ECB_DFR",
      "country": "EU",
      "central_bank": "ECB",
      "rate": 2.25,
      "source": "ECB",
      "source_series_id": "FM/D.U2.EUR.4F.KR.DFR.LEV"
    }
  ],
  "meta": {
    "total": 27179,
    "page": { "offset": 0, "limit": 20 }
  },
  "links": {
    "next": "https://eodhd.com/api/rates/policy-rates?page%5Boffset%5D=20&page%5Blimit%5D=20"
  }
}
```

### Output Format

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| data | array | Array of policy-rate records |
| meta | object | Metadata: total count and pagination |
| links | object | Pagination links (next page URL or null) |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| date | string (YYYY-MM-DD) | Observation date |
| code | string | Policy-rate code |
| country | string | Country / area |
| central_bank | string | Central bank |
| rate | number | Policy rate (percent) |
| source | string | Data provider |
| source_series_id | string | Upstream series identifier |

## Example Requests

```bash
# Fed policy-rate history
curl "https://eodhd.com/api/rates/policy-rates?api_token=YOUR_TOKEN&filter%5Bcentral_bank%5D=FED"

# ECB policy rates from a start date
curl "https://eodhd.com/api/rates/policy-rates?api_token=YOUR_TOKEN&filter%5Bcountry%5D=EU&filter%5Bfrom%5D=2025-01-01"

# Using the helper client
python eodhd_client.py --endpoint rates/policy-rates --filter-param central_bank=ECB --filter-param from=2025-01-01
```

## Notes

- Filters use JSON:API bracket syntax: `filter[code]`, `filter[country]`, `filter[central_bank]`, `filter[from]`, `filter[to]`.
- `filter[code]`, `filter[country]`, and `filter[central_bank]` each accept a comma-separated list.
- Codes and country / central-bank values are upper-case (e.g. `ECB_DFR`, `FED`).
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
