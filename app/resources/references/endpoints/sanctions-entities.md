# Sanctions Screening API — Entities

Status: complete
Source: financial-apis (Sanctions Screening API)
Docs: https://eodhd.com/financial-apis
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /sanctions/entities
Method: GET
Auth: api_token (query)

## Purpose

Searches sanctioned entities (e.g. OFAC) — individuals, companies, vessels, and aircraft — with aliases, structured identifiers, sanctions programs, and listing status. Used for KYC / AML screening, counterparty checks, and compliance workflows. Returns the standard JSON envelope `{data, meta, links}` and is paginated.

## Parameters

> **Query params are bare keys, not `filter[...]`.** Sanctions endpoints use plain query params (`source`, `type`, `program`, ...) while credit-risk and interest-rate endpoints use JSON:API `filter[...]`. Pagination still uses `page[limit]` / `page[offset]`.

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key |
| source | No | string | Source list. Currently only `ofac` is accepted |
| type | No | string | Entity type: `individual`, `entity`, `vessel`, or `aircraft` |
| program | No | string | Sanctions program (e.g. `RUSSIA-EO14024`) |
| country | No | string | Country associated with the entity |
| q | No | string | Free-text search (minimum 2 characters) |
| active | No | boolean | Active listing status. When omitted, only active listings are returned; pass `false` to return ONLY inactive/delisted entries. There is no single-call "all" mode |
| page[limit] | No | integer | Records per page (default 20, max 100) |
| page[offset] | No | integer | Zero-based pagination offset |

## Response (shape)

```json
{
  "data": [
    {
      "source": "ofac",
      "source_uid": "51546",
      "entity_type": "entity",
      "name": "AKTSIONERNOE OBSHCHESTVO GAZPROM SHELFPROEKT",
      "programs": ["RUSSIA-EO14024", "UKRAINE-EO13662"],
      "country": "Russia",
      "remarks": null,
      "listed_date": null,
      "is_active": true,
      "aliases": ["JSC GAZPROM SHELFPROJECT"],
      "identifiers": {
        "Tax ID No.": ["7730250045"],
        "Registration Number": ["1197746185691"],
        "Target Type": ["State-Owned Enterprise"]
      }
    }
  ],
  "meta": {
    "total": 40,
    "page": { "offset": 0, "limit": 20 }
  },
  "links": {
    "next": "https://eodhd.com/api/sanctions/entities?q=Gazprom&page%5Boffset%5D=20&page%5Blimit%5D=20"
  }
}
```

### Output Format

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| data | array | Array of sanctioned-entity records |
| meta | object | Metadata: total count and pagination |
| links | object | Pagination links (next page URL or null) |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| source | string | Source list that designated the entity |
| source_uid | string | Unique id within the source list |
| entity_type | string | Type of entity (individual, entity, vessel, aircraft) |
| name | string | Primary name |
| programs | array | Sanctions program codes |
| country | string or null | Associated country |
| remarks | string or null | Free-text remarks / designation notes |
| listed_date | string (YYYY-MM-DD) or null | Date first listed |
| is_active | boolean | Whether the listing is currently active |
| aliases | array | Known aliases / alternate spellings |
| identifiers | object | Map of identifier type → list of values (e.g. Tax ID, Registration Number) |

## Example Requests

```bash
# OFAC sanctioned individuals in a country (bare query params)
curl "https://eodhd.com/api/sanctions/entities?api_token=YOUR_TOKEN&source=ofac&type=individual&country=Russia"

# Free-text search
curl "https://eodhd.com/api/sanctions/entities?api_token=YOUR_TOKEN&q=Gazprom"

# Using the helper client (--filter-param maps to bare keys for sanctions)
python eodhd_client.py --endpoint sanctions/entities --filter-param program=RUSSIA-EO14024 --filter-param type=entity --filter-param active=true
```

## Notes

- Query params are **bare keys** (`source`, `type`, `program`, `country`, `q`, `active`) — **not** `filter[...]`.
- `source` currently supports only `ofac`.
- `type` accepts `individual`, `entity`, `vessel`, or `aircraft`.
- `q` requires a minimum of 2 characters.
- `active` omitted → only active listings; `active=false` → only inactive/delisted entries.
- `identifiers` is an object mapping each identifier type to a list of values; `aliases` is an array — screen against all aliases, not just `name`.
- Use `/sanctions/programs` and `/sanctions/sources` to enumerate valid program / source values.
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
