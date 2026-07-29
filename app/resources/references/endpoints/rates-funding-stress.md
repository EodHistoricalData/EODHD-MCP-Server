# Interest Rates API — Funding-Stress Spreads

Status: complete
Source: financial-apis (Interest Rates API — SOFR, Fed Funds, ECB, BoE)
Docs: https://eodhd.com/financial-apis/interest-rates-api-sofr-fed-funds-ecb-boe-policy-rates
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /spreads/funding-stress
Method: GET
Auth: api_token (query)

## Purpose

Provides pre-computed funding-stress spreads between two reference-rate legs (e.g. EFFR minus SOFR for code `EFFR_SOFR`), expressed in basis points, with the two component legs and their underlying rates. Used to monitor money-market funding pressure and short-term liquidity stress. Returns the standard JSON envelope `{data, meta, links}`. This endpoint is NOT paginated; if no dates are given, the most recent 30 days are returned.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key |
| filter[code] | No | string | Spread code(s). Values: `EFFR_SOFR`, `OBFR_EFFR`, `TGCR_BGCR`, `SOFR_TARGET_LOWER`, `EFFR_TARGET_MID`, `TARGET_UPPER_SOFR` |
| filter[from] | No | string (YYYY-MM-DD) | Start date |
| filter[to] | No | string (YYYY-MM-DD) | End date |

> This endpoint has **no pagination** (`page[offset]` / `page[limit]` are not used); narrow the result set with `filter[code]` and a date window instead.

## Response (shape)

```json
{
  "data": [
    {
      "date": "2026-07-24",
      "code": "EFFR_SOFR",
      "value_bps": -1,
      "formula": "EFFR - SOFR",
      "leg_a": "EFFR",
      "leg_b": "SOFR",
      "leg_a_rate": 3.63,
      "leg_b_rate": 3.64
    }
  ],
  "meta": { "total": 19 },
  "links": []
}
```

### Output Format

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| data | array | Array of funding-stress spread records |
| meta | object | Metadata (total count) |
| links | array | Empty (this endpoint is not paginated) |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| date | string (YYYY-MM-DD) | Observation date |
| code | string | Spread code |
| value_bps | number | Spread value in basis points |
| formula | string | Human-readable formula (e.g. `EFFR - SOFR`) |
| leg_a | string | First leg rate code |
| leg_b | string | Second leg rate code |
| leg_a_rate | number | Rate value of leg A (percent) |
| leg_b_rate | number | Rate value of leg B (percent) |

## Example Requests

```bash
# EFFR-SOFR funding-stress spread
curl "https://eodhd.com/api/spreads/funding-stress?api_token=YOUR_TOKEN&filter%5Bcode%5D=EFFR_SOFR"

# Funding stress over a window
curl "https://eodhd.com/api/spreads/funding-stress?api_token=YOUR_TOKEN&filter%5Bfrom%5D=2025-01-01&filter%5Bto%5D=2025-12-31"

# Using the helper client
python eodhd_client.py --endpoint spreads/funding-stress --filter-param code=EFFR_SOFR --filter-param from=2026-05-01 --filter-param to=2026-05-31
```

## Notes

- Filters use JSON:API bracket syntax: `filter[code]`, `filter[from]`, `filter[to]`.
- No pagination — the client does not send `page[limit]` / `page[offset]` for this endpoint, and `links` is returned as an empty array.
- If no dates are given, the most recent 30 days are returned.
- `value_bps` is in basis points; `leg_a_rate` / `leg_b_rate` are the underlying rates in percent.

## HTTP Status Codes

The API returns standard HTTP status codes to indicate success or failure:

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| **200** | OK | Request succeeded. Data returned successfully. |
| **402** | Payment Required | API limit used up, or your plan lacks endpoint access. |
| **403** | Forbidden | Invalid API key or plan lacks endpoint access. Check your `api_token`. |
| **422** | Unprocessable Entity | Validation error (e.g. bad filter parameter). |
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
