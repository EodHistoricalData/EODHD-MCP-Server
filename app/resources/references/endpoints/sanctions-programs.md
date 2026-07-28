# Sanctions Screening API — Programs

Status: complete
Source: financial-apis (Sanctions Screening API)
Docs: https://eodhd.com/financial-apis
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /sanctions/programs
Method: GET
Auth: api_token (query)

## Purpose

Lists the distinct sanctions programs with the count of designated entities per program. Use it to enumerate valid `program` values for `/sanctions/entities` and `/sanctions/vessels`, and to gauge program size. Returns the standard JSON envelope `{data, meta, links}`. This endpoint returns the full list and is not paginated.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key |

## Response (shape)

```json
{
  "data": [
    { "program": "RUSSIA-EO14024", "count": 6349 },
    { "program": "SDGT", "count": 3240 }
  ],
  "meta": [],
  "links": []
}
```

### Output Format

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| data | array | Array of sanctions-program records |
| meta | array | Empty (this endpoint takes no query parameters) |
| links | array | Empty (this endpoint is not paginated) |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| program | string | Sanctions program code |
| count | integer | Number of designated entities in the program |

## Example Requests

```bash
# List all sanctions programs with counts
curl "https://eodhd.com/api/sanctions/programs?api_token=YOUR_TOKEN"

# Using the helper client
python eodhd_client.py --endpoint sanctions/programs
```

## Notes

- Takes no query parameters beyond `api_token`; `meta` and `links` are returned as empty arrays.
- Feeds valid values into the `program` parameter of `/sanctions/entities` and `/sanctions/vessels`.

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
