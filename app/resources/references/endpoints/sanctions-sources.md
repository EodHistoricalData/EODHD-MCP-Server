# Sanctions Screening API — Sources

Status: complete
Source: financial-apis (Sanctions Screening API)
Docs: https://eodhd.com/financial-apis
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /sanctions/sources
Method: GET
Auth: api_token (query)

## Purpose

Lists the distinct source lists that feed the consolidated sanctions dataset. Use it to discover valid `source` values for `/sanctions/entities` and `/sanctions/vessels`. Returns the standard JSON envelope `{data, meta, links}`. This endpoint returns the full list and is not paginated.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key |

## Response (shape)

```json
{
  "data": [
    { "name": "ofac" }
  ],
  "meta": [],
  "links": []
}
```

### Output Format

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| data | array | Array of source records |
| meta | array | Empty (this endpoint takes no query parameters) |
| links | array | Empty (this endpoint is not paginated) |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| name | string | Source list name |

## Example Requests

```bash
# List all sanctions sources
curl "https://eodhd.com/api/sanctions/sources?api_token=YOUR_TOKEN"

# Using the helper client
python eodhd_client.py --endpoint sanctions/sources
```

## Notes

- Takes no query parameters beyond `api_token`; `meta` and `links` are returned as empty arrays.
- Enumerates source lists that feed the dataset; currently `ofac` is the accepted `source` filter value on `/sanctions/entities` and `/sanctions/vessels`.

## HTTP Status Codes

The API returns standard HTTP status codes to indicate success or failure:

| Status Code | Meaning | Description |
|-------------|---------|-------------|
| **200** | OK | Request succeeded. Data returned successfully. |
| **402** | Payment Required | API limit used up, or your plan lacks endpoint access. |
| **403** | Forbidden | Invalid API key or plan lacks endpoint access. Check your `api_token`. |
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
