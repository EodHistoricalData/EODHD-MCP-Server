# Credit & Sovereign Risk API — Sovereign Credit Ratings

Status: complete
Source: financial-apis (Credit & Sovereign Risk Data API)
Docs: https://eodhd.com/financial-apis/credit-sovereign-risk-data-api
Provider: EODHD
Base URL: https://eodhd.com/api
Path: /credit-risk/sovereign/credit-ratings
Method: GET
Auth: api_token (query)

## Purpose

Provides sovereign credit ratings from the three major agencies (Moody's, S&P, Fitch) per country. Used for credit-quality screening, mapping ratings to spreads, and eligibility / covenant checks. Returns the standard JSON envelope `{data, meta, links}` and is paginated.

## Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| api_token | Yes | string | Your API key |
| filter[country] | No | string | ISO 3166-1 alpha-3 code, or a comma-separated list (e.g. `USA`, `DEU`, `FRA`). Full country names are NOT matched |
| filter[as_of] | No | string (YYYY-MM-DD) | As-of date; defaults to the latest snapshot |
| page[limit] | No | integer | Records per page (default 20, max 100) |
| page[offset] | No | integer | Zero-based pagination offset |

## Response (shape)

```json
{
  "data": [
    {
      "country_iso3": "DEU",
      "country_name": "Germany",
      "as_of_date": "2026-01-01T00:00:00+00:00",
      "moodys_rating": "Aaa",
      "sp_rating": "AAA",
      "fitch_rating": "AAA",
      "source": "damodaran"
    }
  ],
  "meta": {
    "total": 190,
    "page": { "offset": 0, "limit": 20 },
    "dataset": "sovereign_credit_rating",
    "source": "damodaran",
    "frequency": "annual",
    "attribution": "Damodaran, NYU Stern (annual, sourced from Moody's, S&P, Fitch)."
  },
  "links": { "next": null }
}
```

### Output Format

**Top-level fields:**

| Field | Type | Description |
|-------|------|-------------|
| data | array | Array of sovereign credit rating records |
| meta | object | Metadata: total count, pagination, dataset, source, frequency, attribution |
| links | object | Pagination links (next page URL or null) |

**Data item fields:**

| Field | Type | Description |
|-------|------|-------------|
| country_iso3 | string | ISO 3166-1 alpha-3 country code |
| country_name | string | Country name |
| as_of_date | string (ISO 8601) | Snapshot date (e.g. 2026-01-01T00:00:00+00:00) |
| moodys_rating | string or null | Moody's sovereign rating |
| sp_rating | string or null | S&P sovereign rating |
| fitch_rating | string or null | Fitch sovereign rating |
| source | string | Data provider |

## Example Requests

```bash
# Latest sovereign ratings for Germany
curl "https://eodhd.com/api/credit-risk/sovereign/credit-ratings?api_token=YOUR_TOKEN&filter%5Bcountry%5D=DEU"

# Ratings as of a specific date
curl "https://eodhd.com/api/credit-risk/sovereign/credit-ratings?api_token=YOUR_TOKEN&filter%5Bas_of%5D=2025-01-01"

# Using the helper client
python eodhd_client.py --endpoint credit-risk/sovereign/credit-ratings --filter-param country=DEU
```

## Notes

- Filters use JSON:API bracket syntax: `filter[country]`, `filter[as_of]`.
- `filter[country]` matches ISO 3166-1 alpha-3 codes only (comma-separated list allowed); full country names are not matched.
- Ratings are agency-native strings (e.g. Moody's `Aaa`, S&P/Fitch `AAA`).
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
