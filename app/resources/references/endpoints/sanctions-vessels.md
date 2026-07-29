# Sanctions Screening API — Vessels

Status: complete
Source: financial-apis (Sanctions Screening API)
Docs: https://eodhd.com/financial-apis
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /sanctions/vessels
Method: GET
Auth: api_token (query)

## Purpose

Searches sanctioned vessels (e.g. OFAC) — ships designated under sanctions programs, keyed by IMO number and MMSI and linked back to the owning sanctioned entity. Used for maritime trade compliance, shipping-counterparty screening, and vessel due diligence. Returns the standard JSON envelope `{data, meta, links}` and is paginated. Only currently active vessel listings are returned.

## Parameters

> **Query params are bare keys, not `filter[...]`.** Sanctions endpoints use plain query params (`source`, `imo`, `flag`, ...) while credit-risk and interest-rate endpoints use JSON:API `filter[...]`. Pagination still uses `page[limit]` / `page[offset]`.

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key |
| source | No | string | Source list. Currently only `ofac` is accepted |
| imo | No | string | IMO number |
| flag | No | string | Flag state (e.g. `Panama`) |
| vessel_type | No | string | Vessel type (e.g. `Crude Oil Tanker`) |
| q | No | string | Free-text search (minimum 2 characters) |
| program | No | string | Sanctions program |
| page[limit] | No | integer | Records per page (default 20, max 100) |
| page[offset] | No | integer | Zero-based pagination offset |

## Response (shape)

```json
{
  "data": [
    {
      "call_sign": "3E4045",
      "vessel_type": "Crude Oil Tanker",
      "flag": "Panama",
      "tonnage": null,
      "gross_tonnage": null,
      "owner": null,
      "imo_number": "9282041",
      "mmsi": "352001312",
      "entity_source_uid": "54804",
      "entity_name": "ABHRA",
      "source": "ofac",
      "programs": ["IRAN-EO13902"],
      "country": null,
      "is_active": true
    }
  ],
  "meta": {
    "total": 268,
    "page": { "offset": 0, "limit": 20 }
  },
  "links": {
    "next": "https://eodhd.com/api/sanctions/vessels?flag=Panama&page%5Boffset%5D=20&page%5Blimit%5D=20"
  }
}
```

### Output Format

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| data | array | Array of sanctioned-vessel records |
| meta | object | Metadata: total count and pagination |
| links | object | Pagination links (next page URL or null) |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| call_sign | string or null | Radio call sign |
| vessel_type | string or null | Vessel type |
| flag | string or null | Flag state |
| tonnage | integer or null | Deadweight tonnage |
| gross_tonnage | integer or null | Gross tonnage |
| owner | string or null | Registered owner |
| imo_number | string or null | IMO number |
| mmsi | string or null | Maritime Mobile Service Identity |
| entity_source_uid | string | source_uid of the linked sanctioned entity |
| entity_name | string | Name of the linked sanctioned entity |
| source | string | Source list |
| programs | array | Sanctions program codes |
| country | string or null | Associated country |
| is_active | boolean | Whether the designation is currently active |

## Example Requests

```bash
# Sanctioned vessels by flag state (bare query params)
curl "https://eodhd.com/api/sanctions/vessels?api_token=YOUR_TOKEN&flag=Panama"

# Look up a specific vessel by IMO number
curl "https://eodhd.com/api/sanctions/vessels?api_token=YOUR_TOKEN&imo=9282041"

# Using the helper client (--filter-param maps to bare keys for sanctions)
python eodhd_client.py --endpoint sanctions/vessels --filter-param flag=Panama
```

## Notes

- Query params are **bare keys** (`source`, `imo`, `flag`, `vessel_type`, `q`, `program`) — **not** `filter[...]`.
- `source` currently supports only `ofac`.
- `q` requires a minimum of 2 characters.
- `entity_source_uid` links a vessel back to its owning entity in `/sanctions/entities`.
- Only currently active vessel listings are returned.
- Pagination uses `page[limit]` (default 20, max 100) and `page[offset]`.

## HTTP Status Codes

The API returns standard HTTP status codes to indicate success or failure:

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| **200** | OK | Request succeeded. Data returned successfully. |
| **402** | Payment Required | API limit used up, or your plan lacks endpoint access. |
| **403** | Forbidden | Invalid API key or plan lacks endpoint access. Check your `api_token`. |
| **422** | Unprocessable Entity | Validation error (e.g. bad parameter or pagination value). |
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
